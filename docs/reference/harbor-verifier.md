# Harbor Verifier

This reference owns the shared Harbor verifier under `psycheval.harbor.verifier`,
covering deterministic script checks, continuation gates, score publication, and
the optional YAML LLM Judge. Host execution and Task input preparation live in
[Harbor integration](harbor.md); document inspection and evidence publication
live in [Document inspection and evidence](document-evidence.md).

## Script checks and weighted scoring

The ordinary verifier CLI accepts `grader.json` through the existing `test.sh`
and `test.bat` entrypoints. `custom_checks` declares a list of unique nonempty
UTF-8 check IDs implemented by a sibling `test_outputs.py`. The script and
declaration must either both exist or both be absent. Custom-only configurations
do not require a trajectory. Registration and preview never execute Task code.

The script runs as native Python argv with `--context <path>` and
`--output <path>`. Context uses the runtime JSON protocol's `paths`: `workdir`,
`tests`, `artifacts`, `agent_logs`, `verifier_logs`, and nullable `inputs` and
`preparation_state`. It can read the current
step's ATIF from `agent_logs/trajectory.json` when available. GT and helpers live
beside the staged script, outside the Agent workspace. Each verification resets
its uploaded test context before applying Harbor's shared/step overlay rules.
This staging is not a host filesystem sandbox.

The output is UTF-8 JSON of the form
`{"checks":[{"id":"values","passed":true,"evidence":"matched GT"}]}`.
`passed` must be boolean; `evidence` is optional text. Unknown or duplicate IDs
are errors. A normal exit with missing declared checks scores those checks zero
and records them as missing. Nonzero exit, malformed or missing output, and
timeout are verifier errors, not Agent failures. Stdout and stderr are logs.
The CLI limits grader and script-result JSON to 16 MiB and ATIF JSON to 128 MiB.
Harbor's verifier deadline covers custom scripts and all of their descendants.

`build_scoring_plan(config)` declares all scoring items before execution.
Built-in IDs retain their existing names; script IDs become `custom:<id>` in
the `custom_outputs` dimension. `scoring.weights` maps declared IDs to finite
nonnegative weights, defaulting to one; total weight must be positive. For
example, `{"custom_checks":["values","format"],"scoring":{"weights":
{"custom:values":3,"custom:format":1}}}` awards 0.75 when only values passes.

Optional `scoring.descriptions` maps the same declared check IDs to nonblank
UTF-8 text describing what each rule checks. For example,
`{"custom:values":"Check output values against the reference data."}` describes
the `values` script check. Authors may describe any subset of the plan. The
descriptions are review metadata used by the Task inventory and previews.

`aggregate(checks, *, plan)` computes `sum(weight * passed) / sum(weight)` over
the complete plan. Dimension scores use the same rule; dimensions with no
positive weight score one, including dimensions containing only zero-weight
checks. These values do not establish that those checks passed. `evaluate` only
evaluates built-in checks and never executes Task code.
Dataset-owned scorers and WorkBuddy scoring retain their own policies.

### Continuation checks

`grader.json` may declare `continuation_checks`, a nonempty list of unique
deterministic check IDs from the same scoring plan, including `custom:<id>`.
Unknown IDs, duplicate IDs, empty lists, and LLM rubric references are
configuration errors. Check weights do not affect this condition; zero-weight
checks are allowed, while total scoring weight must still be positive.

When configured, `aggregate` also returns `continuation`: one only when every
referenced check passed, otherwise zero. A normally completed script that omits
a referenced check fails the condition. Without the declaration, the key is
absent. Script and configuration errors remain verifier errors with no current
reward. The condition neither adds a scoring item nor changes quality rewards,
dimension scores, check counts, or `test_status`.

Use Harbor's existing step setting `min_reward = { continuation = 1.0 }` to
stop subsequent steps when this condition fails. Gate decisions use each step's
own result. Harbor's `mean` strategy averages every numeric reward key; a root
Trial's averaged `continuation` is not a whole-Trial pass/fail decision. A missing
gated key or verifier result cannot pass the threshold; globally disabled
verification skips Harbor's threshold check.

`reward.json` publishes the numeric condition unchanged by Judge merging.
`score.json` records `metadata.continuation` with `passed`, ordered `check_ids`,
`failed_check_ids`, and `missing_check_ids`. Failed IDs include missing checks;
their existing deterministic verdicts retain the reasons. No additional verdict
or rubric is created. Quality success and permission to continue are separate:
even a quality score of one cannot override a failed continuation condition.
Task previews expose the referenced IDs without counting them as extra checks.

For example, a delivery-only continuation condition can reference
`["required_artifacts", "final_answer"]` while those checks have zero scoring
weight and a substantive custom check carries the quality score. Allowing an
independent next step after an upstream outage does not grant coverage or
substantive quality credit for the failed retrieval.

### Score publication

`reward.json` contains numeric results. `score.json` uses the Office score
envelope: final `reward` and `overall`, `test_status`, unweighted
`test_pass_rate`, `tests_passed`, `tests_total`, `verdicts`, `judges`,
`diagnostics`, and `metadata`. Counts include all declared deterministic checks;
`test_pass_rate` is `tests_passed / tests_total` (zero for no checks). The rule
group's `scores.pass_rate` has the same meaning; its `scores.overall` and
`metadata.score_merge.rule_score` retain the weighted rule score used in reward.
Status follows Office's finalizer: `full_pass` for
reward one, `partial_pass` for a positive reward below one, and `no_pass` for zero.
Values retain their full precision.
These statuses describe the quality score, not permission to execute another
step. A `full_pass` may coexist with a failed zero-weight delivery check and
`metadata.continuation.passed=false`; inspect the
[continuation condition](#continuation-checks) for control flow. Neither
`test_status` nor a dimension's neutral zero-weight score establishes that all
required checks passed.

Each deterministic check has an Office-shaped verdict with its existing
`item_id`, binary `status` and `score`, `reason` from check evidence,
`judge_name`, `judge_type`, `evidence_ids`, nullable `confidence`, and `metadata`.
Metadata retains dimension, weight, and missing-result state. Missing checks
fail. The `rule` judge (`rule_script`, family `rule`) groups those verdicts and
retains dimension scores. Top-level verdicts flatten judge groups in declaration
order. No separate plan or legacy checks payload is published.
Group `ok` means execution was nonfatal, not that all verdicts passed. The
Office status-count vocabulary includes zero-valued categories without local
producers (`review`, `build_error`, `judge_error`).
Total rule weight is the sum of check weights. A fresh
temporary output is used for each script invocation. Prior reward, score, and
legacy check outputs are removed before evaluation; successful outputs are
atomically replaced, with reward published last. Errors retain diagnostics and publish no
reward for the invocation.

## YAML LLM Judge

Retained prompt inspection and independent rubric execution are described in
[Judge inspection and runs](judge-runs.md). The public `prepare_judge` and
`run_judge` interfaces share the normal verifier's evidence and model-call logic.

The shared verifier optionally reads `tests/judge.yaml`. Its version-1 schema
uses `artifacts`, `llm_judge`, and `score_merge`, independently of `grader.json`.
YAML is safely parsed with strict types, unique mapping keys and IDs, known
methods, contained relative artifact paths, and resolved artifact references.
Configuration reads are bounded to 1 MiB, with at most 64 artifacts, 32 rubrics,
and 8 artifact references per rubric.
Task discovery and preview never execute preparation, verification, or model
calls. Shared tests are overlaid by step tests; a step's YAML replaces the whole
shared file. This contract does not replace WorkBuddy's own judge runtime.

Each artifact declares exactly `id`, `path`, boolean `required`, and nonempty
`type`, matching WorkBuddy Office declarations. `source` is not accepted.
The declared type is preserved, including binary types such as `xlsx`.
Custom scripts own extraction from original files into UTF-8 text; the Judge
does not convert binary formats or read original files through `source_path`.

Evidence comes from `verifier_logs`. When `artifact_manifest.json` exists, it
must be a UTF-8 JSON object with an `artifacts` list of records with unique IDs.
Record IDs match declaration IDs exactly, without trimming whitespace.
A matching record takes precedence: `extract_status: ok` reads its `text_path`,
relative to `verifier_logs`; other statuses do not fall back to the declaration.
Additional Office metadata is accepted, and undeclared records are not read.
Only when no matching record exists can a text declaration read its `path`
directly under `verifier_logs`. Text recognition follows Office's text-like
types, including `text`, `markdown`, `yml`, and source-code types; matching
ignores case and a leading dot. Other types without a record are missing evidence.
Types are intentionally open-ended for task-owned extractors: an unrecognized
type, including a misspelling such as `makrdown`, is not a YAML validation error.
When evidence loading completes, `judge/evidence.json` records extraction
requirements and path read errors. A whole-Judge evidence failure, such as an
invalid manifest or exceeded evidence budget, prevents this index from being
published; inspect the LLM group's metadata reason in `score.json` instead. Check the declared type
and matching manifest record before investigating the model.
The index maps artifact IDs to read diagnostics, retaining `required`,
`extract_status`, and `error`, plus the selected `text_path` relative to
`verifier_logs`, `byte_count`, and `sha256`. It stores no `text` body.
When no path is selected or its relative-path syntax is invalid, `text_path` is
null. A syntactically valid path is retained even if its file is missing,
unreadable, linked, or invalid UTF-8. Size and hash describe the same raw
bytes that were successfully read and decoded as UTF-8; they are null when no
valid text was obtained. Empty text has zero bytes and the empty-content hash.
The source text file remains authoritative; the fingerprint permits checking
whether retained source content has changed since the Judge read it.

Manifest reads are bounded to 1 MiB; text reads share the configured evidence
budget. Both use contained regular files, rejecting links, absolute paths,
traversal and invalid UTF-8. There is no workspace scan, URL retrieval, rendering,
or silent truncation. Custom scripts can read the current-step ATIF from their
`agent_logs` runtime path and publish final answers and source material in
`verifier_logs/artifact_text/`, directly or through a manifest. Scripts own
refreshing evidence outside the framework-managed directories below.
`final_answer_text(trajectory)` returns the last nonempty Agent message in the
supplied trajectory, including messages with tool calls. Text blocks are joined
with newlines; reasoning, observations and child trajectories are not searched.
Built-in final-answer checks use this same helper. This is retained trajectory
text, not a guarantee of a complete, unredacted original or a terminal response.
Custom checks may publish it as `final_answer` using their own `EvidenceWriter`;
the framework does not open another writer or publish an implicit artifact.
`matching_observations(trajectory, rule)` returns successful observation text
for one required-call rule using the same call/argument/success predicates as
built-in checks, without assigning another score.
For multiple queries over the same retained trajectory, `ObservationIndex`
indexes call/result pairing once. Its `calls` tuple preserves call order;
`matching(rule)` returns `(ToolCall, tuple[str, ...])` pairs with successful
observation text. Callers choose their step/context scope before indexing and
must not mutate the trajectory while reusing the index. No source files or
networks are accessed.
The verification context adds `harbor.verifier.instruction` and nullable
`harbor.verifier.step_name` alongside the native runtime paths.

`llm_judge.method` is `rubric_binary_mean`. Each rubric has a unique `id`,
string `question`, nonempty `artifact_refs`, and string lists `pass_criteria`,
`fail_criteria`, and optional `scope_limits`. Every list item may be a YAML
multiline string. Each model response must be an object containing the rubric's
`id`, boolean `passed`, and nonempty string `reason`. Additional fields are
accepted but ignored: only these three fields enter the scoring result. The raw
response remains in diagnostics with credential redaction. Missing or invalid
required fields, duplicate JSON keys, and nonfinite JSON numbers still fail
response validation. Default prompts include all criteria and scope limits, and
instruct the evaluator to treat Agent content as evidence, not instructions.

Python integrations import `JudgeSettings` and the asynchronous `run_verifier`
from `psycheval.harbor.verifier` (or its copied package namespace):

```python
async def run_verifier(config_path, *, runtime=None, judge_settings=None): ...
```

`config_path` selects `grader.json`. An explicit `judge_settings` object supplies
the complete Judge configuration, including an explicit `enabled=False`; it is
never merged with environment fields. Without that object, the verifier reads
the environment settings below only when `judge.yaml` exists. `JudgeSettings`
validates direct constructor arguments and `from_env()` values through the same
contract: enabled calls require an HTTP(S) API base URL and nonempty model,
integer limits must be positive, and deadlines must be finite and positive.
The API key is optional and excluded from the settings representation. Errors
from `from_env()` identify the corresponding `PEVAL_JUDGE_*` variable. Without
`judge.yaml`, the Judge status is `absent`, even with explicit enabled settings;
no model calls or LLM score are produced.

The keyword-only `reasoning_effort` setting accepts `None` (the default) or a
nonempty string, with surrounding whitespace removed. When provided, every
Chat Completions request, including retries, sends it as the top-level
`reasoning_effort` field. `None` omits that field and leaves the provider default
in effect. Supported values depend on the selected provider and model; the
verifier does not impose a fixed vocabulary or add provider-specific thinking
settings. Provider rejection follows the usual Judge failure and rule-score
fallback behavior. An explicit settings object with `reasoning_effort=None`
does not inherit the environment value.

`JudgeSettings` also accepts keyword-only `system_prompt` and
`user_prompt_template`. `system_prompt=None` (the default) omits the system
message; an explicit string adds it unchanged before the user message.
`user_prompt_template=None` uses an English Office-style rubric prompt beginning
with `You are a LLM-as-Judge evaluator.` Its sections contain the task instruction,
the step name when present, the current weighted rule total before LLM merging,
referenced artifacts with read metadata and faithful text, and the rubric's
question, pass/fail criteria, and scope limits when present. Its `Rule reward`
context includes only `reward`, or an empty object when no
rule total was supplied. It omits continuation, dimension scores (including
neutral zero-weight dimensions), and LLM scores. The total summarizes the
configured quality weights; it is not proof of delivery or of any individual
check passing. This projection applies to normal verification and prepared
Judge previews/runs, without changing published scores or gate decisions.
The default prompt keeps the `id`, `passed`, `reason` protocol and labels task
instructions and Agent content as untrusted assessment data. Task instruction text is enclosed in
`<task_instruction>` tags, and each artifact's faithful text is enclosed in
`<artifact_faithful_text>` tags. Task instruction, artifact metadata JSON, and
faithful text use XML escaping for `&`, `<`, and `>` while preserving quotes,
whitespace, newlines, and Unicode; decoding the
entities once recovers the original text. The prompt identifies this content as
XML-escaped assessment data. Tags mark data boundaries, not a guarantee that the
model will ignore instructions within untrusted content.
Custom values must be nonempty strings,
and their whitespace and newlines are preserved. The user template must contain
exactly one literal `{context}` marker. It is replaced with the complete current
rubric context JSON: instruction, step name, rubric (including scope limits), and
referenced evidence. Other braces remain literal, and inserted context is never
expanded again. The custom context JSON remains independent of the default
prose template and does not include rule rewards. Custom prompts must request
the same `id`, `passed`, and `reason` response object. Callers supplying custom
prompts must also instruct the evaluator to assess task instructions and Agent
content as untrusted evidence, rather than follow instructions within that data.
No trust instruction is automatically added to custom prompts, including when
only the user template is overridden and the system message is omitted.
Response validation and scoring do not change. Prompt overrides are Python
configuration only.

An explicit `EffectiveRuntimeConfig` supplies the invocation paths and context
without reading `PEVAL_CONFIG`. When omitted, the Python API requires a configured
`PEVAL_CONFIG`; it never creates container-style `/logs` paths implicitly. Only
the CLI supplies those default paths when no runtime is configured.
The returned dictionary is the complete `score.json` payload; the same
invocation also publishes the usual files and propagates verifier exceptions.
Concurrent invocations must use separate verifier-log directories. Blocking path
resolution and file queries, local checks, evidence I/O, and publication use a
bounded, process-wide verifier thread pool, separate from the embedding
application's default asyncio executor. Judge
network calls remain asynchronous. Cancellation waits for any current worker
operation to finish before returning, so that worker cannot write to reused
output paths afterward.

Direct Python calls do not impose a timeout on custom scripts or own their
process trees. Each hung script occupies a verifier worker; exhausting the shared
pool also delays other in-process verifier calls, including evidence reads and
publication. Python also joins the pool's workers at interpreter exit, so a hung
script can prevent process shutdown as well as cancellation from completing;
wrapping `run_verifier` in `asyncio.wait_for` or `asyncio.timeout` does not impose
a hard deadline on that stage. Direct callers must use scripts whose completion
they control. Applications needing enforced execution deadlines should run the
verifier through a Harbor Job and configure its verifier timeout: that enclosing
command owns process-tree termination. This ownership applies to the Harbor
execution path, not an arbitrary Python caller or standalone CLI process.
The CLI uses this API through `asyncio.run()`.

LLM calls are disabled by default. Harbor `verifier.env` supplies these settings
when no explicit `JudgeSettings` is passed:

| Variable | Meaning / default |
| --- | --- |
| `PEVAL_JUDGE_ENABLED` | `true` enables calls; default `false`. |
| `PEVAL_JUDGE_BASE_URL` | OpenAI-compatible API base URL, including `/v1` when required. |
| `PEVAL_JUDGE_MODEL` | Model name; required when enabled with a judge configuration. |
| `PEVAL_JUDGE_API_KEY` | Optional bearer credential; use an environment reference. |
| `PEVAL_JUDGE_REASONING_EFFORT` | Optional reasoning effort, for example `high`; omitted when unset. An empty or whitespace-only value is invalid. |
| `PEVAL_JUDGE_CONCURRENCY` | Concurrent rubric requests, default 4. |
| `PEVAL_JUDGE_REQUEST_TIMEOUT_SEC` | Per-request deadline, default 30 seconds. |
| `PEVAL_JUDGE_TOTAL_TIMEOUT_SEC` | Complete Judge deadline, default 120 seconds. |
| `PEVAL_JUDGE_MAX_EVIDENCE_BYTES` | Combined declared evidence limit, default 1 MiB. |

The verifier validates configuration, runs built-in and custom checks, collects
fresh evidence, calls Chat Completions, and then merges scores. Temporary network
errors, HTTP 429, and server errors receive at most one retry. Each rubric is
binary and equally weighted. `score_merge.method` is `weighted_sum`;
`rule_weight` and `llm_weight` default to 0.8 and 0.2, must be finite and
nonnegative, and must have a positive sum. Complete results use:

```text
llm_score = passed rubrics / declared rubrics
reward = (rule_weight * rule_score + llm_weight * llm_score)
         / (rule_weight + llm_weight)
```

An incomplete rubric due to API, timeout, evidence-size, or response-protocol
failure disables the entire LLM merge for that invocation. The rule score is
retained with a reason, and no `llm_score` is published. An unreadable or malformed
manifest, including duplicate IDs or JSON keys, likewise disables the LLM merge
without calling the model. Missing, invalid or empty required evidence fails
the referencing rubrics. Missing optional evidence permits assessment; optional
evidence with a read or extraction error fails its referencing rubrics.
Invalid configuration and failed custom scripts remain verifier errors.
An overall Harbor verifier timeout or cancellation still fails the Trial through
its normal lifecycle. The Judge never provides an LLM-only scoring mode.
Results finishing after the Judge total deadline remain incomplete, even when
all rubric responses are available after synchronous diagnostic I/O; they do not
enable score merging.

`reward.json` contains the final reward, rule dimensions, `rule_score`, the
optional [continuation condition](#continuation-checks), and, only when complete,
`llm_score`. `score.json` adds `llm_judge_component_score` only
when the Judge completes. Its `llm_judge` group (type `llm_judge`, family `llm`)
contains one verdict per rubric with `llm:<id>`, evidence references, and rubric
criteria in metadata. Unassessed rubrics use `abstain` with a null score;
completed verdicts remain visible even when the group is incomplete. Disabled
and incomplete groups have no component scores. Group metadata records
completion state, reason, and elapsed time; errors use the Office errors array.
Without `judge.yaml`, the LLM group is absent.

`metadata.score_merge` records the method, configured weights, available component
scores, final score, applied flag, and reason. Diagnostics contain status counts
and declared evidence metadata, without repeating a plan. This serialization
does not import the WorkBuddy runtime or adopt its rounding or error policy.
These result files and `judge/*.json` diagnostics use UTF-8 with two-space
indentation and a trailing newline. Chinese and other Unicode text remain
readable; isolated surrogate code points are escaped to preserve valid UTF-8.
JSON string escaping, including nested model-response text, is preserved.
`judge/` contains the evidence read index, request messages, model responses,
request timing, and available token usage, without connection credentials.
Each `rubric-xxxx.json` stores the `messages` supplied to the provider at the
top level, shared by its retry attempts. This prompt-debugging snapshot includes
the rendered system/user prompts and referenced evidence text. Evidence referenced
by multiple rubrics is repeated in their request snapshots, so the total
diagnostic size grows with the number of rubrics sharing that evidence; the
evidence-read budget is not a total diagnostic-size cap. When no request
is attempted, `messages` is null. A recorded attempt does not establish provider
receipt; its response or error retains that distinction. Known credentials are
redacted from diagnostics in both original and XML-escaped forms, including
nested JSON escaping, without changing the messages submitted to the model.
Credentials shorter than eight characters match only whole word-delimited
values in retained text, preserving ordinary words that contain the same fragment.
These files are diagnostic, not another score authority. Every invocation removes
previous framework scores, `judge/`,
`artifact_manifest.json`, `artifact_text/`, `raw_artifacts/`, `judge_evidence/`, and the legacy
`judge-evidence/` directory before scripts run, without following links.
Successful results are atomically published with reward last; verifier errors
retain diagnostics without a current reward.
`judge/` is reserved for framework diagnostics and is recreated after custom
scripts finish, without following links.
