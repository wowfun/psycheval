# Judge inspection and runs

The generic YAML Judge supports three separate actions: reading a retained
request, previewing a draft, and executing selected rubrics. Reading and
previewing make no model calls and require no resolved credentials. WorkBuddy's
independent Judge runtime is not a generic-Judge execution target.

## Inputs and authority

One input selects one finished Harbor Trial or step through a workspace source
reference or an explicit Trial directory. A multi-step root requires a step.
Completion comes from the Trial root's `result.json`: either the Trial has
finished, or the selected entry in `step_results` has a finished verifier stage.
Step directories need no separate result file.
Rubric selection is explicit: one or more unique IDs, or all declared rubrics.
Unknown IDs fail before evidence access or model calls. Only evidence referenced
by the selection is read, using the verifier's existing containment and size
limits. No Agent, Task preparation, grading script, or document extraction runs.

Generic evaluations retain rubric definitions, evidence declarations and rule
scores in `verifier/score.json`. Its Judge metadata also retains the invocation
instruction, step and non-secret settings. Evidence text stays in the existing
Trial files; `judge/evidence.json` records its paths, statuses and fingerprints,
and `judge/rubric-*.json` records actual requests. There is no additional full
input dump in the Trial. Preview returns rendered messages, non-secret settings
and an input fingerprint. It creates no server cache or preparation token.
Execution prepares inputs again. If an optional preview fingerprint differs,
execution reports a conflict before resolving credentials or calling the model;
the caller must preview again. Prompt construction and model execution remain
owned by the relocatable Harbor verifier. Its public `run_judge` accepts prepared
inputs and returns results and diagnostics without an output directory. Normal
verification retains diagnostics through a callback. A callback receives redacted
records and owns retention; execution does not also accumulate those records.
Without a callback the public runner returns full diagnostics in memory.
The application service collects only rubric IDs, messages and results, omitting
raw provider responses and evidence indexes from trial-run responses and exports.
No temporary files are used.

Missing historical instruction/configuration must be explicitly supplied by a
Task directory, instruction file, or draft. Current Task data is labelled as
such; prompt text is never parsed to invent historical context. Missing required evidence
keeps the ordinary Judge's fail semantics; model/protocol failures produce
unassessed outcomes.

## Retained requests

Prompt lookup matches the `id` inside `judge/rubric-*.json`, never the file's
ordinal. It returns the recorded messages, request attempts and known settings.
It does not require the Task, current profiles or API keys. A recorded attempt
does not prove provider receipt. A null message array with no attempts means no
request was made; an absent snapshot means the request was not retained.
Neither condition silently triggers preview or execution.

Messages retain role order, Unicode, line breaks and literal escaping. Reads
apply retained-content credential redaction. Bounded previews declare truncation;
complete exports remain subject to bounded safe reads. Diagnostic files are not
another score authority.

## Profiles and storage

`peval.toml` owns `[judge]` with an optional `default_profile` and a `profiles`
mapping. Each named profile supplies a title, Chat Completions base URL, model,
optional reasoning effort and prompt overrides, execution limits, and an optional
API key environment reference such as `${DEEPSEEK_API_KEY}`. Literal credentials
are rejected. Credentials resolve only when execution starts, on the server.
An explicitly selected profile wins over the configured default; missing profiles
are errors. Existing normal-verification `PEVAL_JUDGE_*` settings are independent.

Trial runs write no files and never change Trial rewards, source Tasks,
configuration, catalog scores or Jobs aggregates. Known credentials are removed
from returned data. The shared service is stateless: it has no run directories,
IDs, task registry, process ownership, history, recovery or polling. Existing
`judge-runs/` data is neither read nor deleted.

`POST /api/judge/{source_key}/preview` returns a preview;
`POST /api/judge/{source_key}/run` executes within the request and returns one JSON
result. A fingerprint mismatch returns HTTP 409. Client abort or disconnect
cancels execution and releases its tasks; no partial response is retained and no
automatic restart occurs. Ordinary deadlines and model failures return completed
assessments plus unassessed items. Cancellation is distinct from rubric failure.

## CLI and workbench

`peval judge inspect`, `prompt`, `preview` and `run` share the
application service. `--source-ref` and `-p` are mutually exclusive; `--step`
selects a phase when using a Trial directory. `--rubric` repeats; `--all` selects
all. `--judge-config`, `--task` and `--instruction` are explicit draft inputs.
`inspect --export-config` writes an editable YAML draft. `--json` returns structured data and `-o`
exports it. Exports require a new output file and never replace existing inputs.
`run` exits 0 for complete assessments, including failed rubrics, 1 for
incomplete or cancelled execution and 2 for invalid input. Runs execute directly;
Ctrl+C cancels. Default output goes to stdout without creating files.
Options unrelated to the selected subcommand are rejected. `inspect` text output
summarizes the source and rubrics; `--json` returns the complete inspection.

Multi-step Trials appear as individual step rows in the workspace catalog;
select the desired row to inspect or try that step's rubrics.
The Verification panel offers retained prompts directly from each rubric and
one trial panel for editing rubrics, choosing a profile, previewing, running,
cancelling and reading results. Results show original to current verdict and
reason, with expandable actual messages. Missing baselines remain explicit.
Drafts and only the latest attempt per Trial live in page memory. Closing the
panel, changing Trials or navigating within the application preserves them;
refreshing or closing the page clears them. No browser storage API is used.
Only one execution is active per page. Navigation does not cancel it, and its
response belongs to its original Trial. Starting again replaces the prior result;
explicit cancellation shows cancelled and discards any unreturned partial result.
Copy, download and explicit CLI exports remain available.

Retained-source queries keep their existing permissions. Profile edits and both
POST operations require an administrator and the existing same-origin guard.
Public reads do not expose server paths or credential configuration.

One run selects one Trial/step, one profile and one rubric set. There is no
score-application action, batch regression or provider-specific protocol adapter.
