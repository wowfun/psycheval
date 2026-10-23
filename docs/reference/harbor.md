# Harbor Integration

Psycheval supports the public Harbor `0.24.0` contract through
`psycheval.harbor`.

Agents declare explicit Harbor capabilities. Unsupported capabilities fail before
use; native Host OpenCode does not implement simulated-user bridges or
`disable_web_search=True`. Its options model is shared by preflight and direct
construction. Jobs reject nonempty inline `extra_instructions` and `user_agent`;
file-based extra instructions remain supported. HostVerifier also rejects inline
extra instructions rather than grading a different instruction from the Agent.
ACP Skill admission uses `capabilities.skills`, including subclass declarations.
Hermes retains upstream ATIF, Skills and MCP support, adds exact-session resume,
and does not support loading native or ATIF trajectories.

Task publication and revision hashing include top-level `trajectory.json`.
Structural validation uses resolved paths; reader callbacks preserve the caller's
lexical root, including Windows short paths, without relaxing containment checks.

## Host ACP Agent

`psycheval.harbor.acp_agent:HostACPAgent` evaluates a preinstalled ACP v1 Agent
on a native Linux or Windows Host and reports the Agent name `acp`.
`argv` is literal executable/argument input. `config_dir` seeds
isolated XDG configuration once; linked entries are rejected. HOME/XDG state
stays private and stable within a Trial, separately from per-invocation evidence.
Only explicitly supplied configuration is copied; ambient user configuration is
not discovered. The child receives effective Agent environment with generated
isolation paths taking precedence and evaluation control variables removed.

`config_options` is an ordered mapping of exact advertised select or boolean IDs to values.
It is applied and confirmed before prompting; dependent options follow their
prerequisites. `model_name` is only a reporting label. Authentication is attempted
only with `authenticate_method_id`. Client filesystem/terminal services and
generic Skills injection are unsupported. Vendor adapters may inject Skills
through native configuration. MCP transport capabilities are negotiated.
Resume uses the exact saved Session and setup, preferring advertised resume over
load; load replay is excluded using wire order. Recovery never creates a replacement.

### Live session updates

`on_session_update` accepts a synchronous or asynchronous callback receiving one
raw `params.update` dictionary. It runs in the parent event loop, in receive
order, for the current invocation's prompt-phase `session/update` notifications.
Setup notifications and restored history are excluded. ACP field names, tool-name
extensions and vendor metadata are preserved; no token accounting is synthesized.
`HostWorkBuddyAgent` inherits this interface. With no callback, no observer runs.

The observer incrementally decompresses the flushed `acp.events.ndjson.gz`; it
does not create another evidence channel. Callback mutations do not alter retained
evidence. Live notifications are provisional presentation data: final evidence
integrity, cleanup and grading still use the existing validation boundary.

Delivery is best effort. A callback or observer failure logs one categorical
warning without notification contents or exception messages, then disables delivery
for that invocation. The next invocation starts a fresh observer. Asynchronous
callbacks and final draining have separate internal five-second deadlines; a
timeout also disables delivery. Synchronous callbacks must return promptly and
asynchronous callbacks must cooperate with cancellation. Callbacks should only
observe updates; the caller manages Agent and Host lifecycle outside them.
Observers close before evidence publication, including after failure or
cancellation, and no callback runs after the invocation returns.
See the [downstream callback examples](../user/downstream-vendoring.md#observe-live-acp-updates)
for direct Python and Harbor configuration integration.

### Permissions and evidence

`permission_mode=allow|deny` prefers the corresponding once option, then always.
Unavailable policy choices cancel the request and fail the invocation. Decisions
are retained. `tool_result_format=acp|rsiversi|codebuddy` defaults to ACP status semantics;
the RSIversi policy additionally interprets the native ToolResult envelope and
recognizable process outcomes independently of tool name. A running background
command, timeout, signal, nonzero exit or unknown terminal result cannot prove
successful execution.
Tool-name grading requires the Agent's non-standard `name` extension on tool
updates. The pinned ACP v1 SDK schema does not define a canonical tool-name field;
`title` is presentation and cannot establish identity. The adapter explicitly
validates and retains `name` from the raw wire before SDK projection. Agents
without this extension remain usable for artifact and answer grading, but
missing identity or incomplete protocol evidence cannot pass name-based rules.
Observation terms inspect delivered content blocks; RSIversi process observations
use stdout/stderr text, excluding execution metadata. Raw structured results
remain in observation extras and do not become synthetic observation text.

Raw frames and stderr are streamed to current-call gzip logs before SDK projection:
`acp.stdin.ndjson.gz`, `acp.stdout.ndjson.gz`, `acp.events.ndjson.gz` and
`acp.stderr.log.gz`. Compression is lossless, including notification order and
vendor fields. Each write synchronously flushes compressed data for live readers.
The harness records the host UTC time of successful prompt submission in
`acp.summary.json` as `prompt_submitted_at`. The current user step carries this
timestamp with `extra.timestamp_source=acp_prompt_submission`, including after
resume. It supplies a recorded date anchor, not Agent inference timing.
Evidence without a recorded submission time keeps that timestamp absent.
New invocations also retain a versioned client clock: one UTC origin and
monotonic nanosecond offsets captured at send/receive boundaries, before evidence
processing. Each invocation owns its clock; offsets never span resume boundaries.
Raw peer messages and vendor timestamps remain unchanged. Conversion uses only
the client clock for observed intervals and marks the trajectory's timestamp
semantics as `event_observed`, disabling adjacent-timestamp duration estimates.
Agent output duration spans the first and last text/thought chunks in a canonical
step; a single chunk supplies a timestamp but no duration. Tool timing spans the
first `in_progress` notification to the first terminal notification. Without an
`in_progress` boundary, an independent initial call and terminal notification
supply a lifecycle observation that can include waiting. Duplicate notifications
do not reset boundaries. Missing, invalid or conflicting boundaries retain
unknown timing with diagnostics, without changing execution or grading outcomes.
Durations are nonnegative integer milliseconds; distinct boundaries can measure
zero. Tool duration and its source live in observation extras; call extras supply
the start timestamp. Older evidence without a client clock remains untimed.
These client-observed intervals are not provider inference, TTFT or decode timing;
their report presentation follows the [telemetry contract](state-and-data.md#telemetry).
Each invocation shares a finite `max_evidence_bytes` stored-byte budget across
these files. `max_decoded_evidence_bytes` separately bounds their combined
uncompressed size; `None` uses the stored-byte budget. Both limits require positive
integers. Peer-derived summary metadata consumes both budgets. Admission reserves
gzip closing space so exhaustion can retain a complete compressed prefix.
Closing attempts every evidence file even if an earlier close fails, then reports
the first failure.
Exhaustion fails the invocation, marks protocol
evidence incomplete, retains its admitted prefix, and still settles descendants.
The bounded wire frame admits inline image results. Frame-count admission scales
with the declared evidence-byte budget up to an independent finite ceiling;
larger retained-evidence budgets can therefore support longer streamed tool output.
The fixed cleanup and
integrity records are retained even when admission is exhausted.
The strict wire limits and byte-budget default belong to
[`acp_protocol`](../../src/psycheval/harbor/acp_protocol.py).
The closed evidence files are bound to an invocation by a summary manifest of
stored and decoded sizes and digests. Bounded streaming readers validate gzip
completion, reject trailing data, and enforce decoded-byte and record limits.
Missing, truncated or substituted retained files fail
conversion explicitly. Publication failures cannot admit partial evidence.
Malformed known protocol data fails explicitly. Context/capacity usage is not
token accounting; absent token and cost evidence remains unknown. Conversion is
performed once by Harbor post-run context population, including partial prompts.
Configuration failures do not fabricate a user turn.

The harness owns a Linux subreaper or a Windows Job and all Agent descendants, including separate
tool process groups. Every outcome attempts bounded cleanup before verification.
Linux cleanup deduplicates each signal by stable process identity, including
kernel start time, so wall-clock adjustments cannot signal the same descendant twice.
`shutdown_timeout_sec` is a shared cleanup deadline with a reserved forced-cleanup
interval. On both platforms, cooperative exit may use all time before that
reserve; Windows then terminates the Job and confirms it is empty.
`handshake_timeout_sec` bounds the entire setup sequence, including
initialization, authentication, Session restoration and configuration selection;
each RPC consumes the remaining deadline. Defaults belong to
[`HostACPAgent`](../../src/psycheval/harbor/acp_agent.py).
Cancel delivery and connection teardown are bounded by the cleanup deadline;
another stop signal interrupts cooperative waits. Cleanup failures still retain
categorical summary evidence.
On a fatal protocol or evidence failure, cooperative waiting stops. The harness
settles the SDK reader before taking over stdout in discard mode; stderr keeps
draining. Forced termination, pipe EOF and task settlement share the same absolute
deadline. Cleanup confirmation requires all three, even if the Job is already
empty. Cleanup diagnostics retain the first failing stage and its error while
later stages still settle; they do not replace the primary execution error or
retain discarded payloads.
If the harness exits before publishing its invocation summary, its captured
stdout/stderr tails are retained in `acp.harness.stdout.log` and
`acp.harness.stderr.log`, bounded separately by a combined `max_evidence_bytes`
cap with stderr taking priority. These diagnostics cannot establish protocol
evidence.
On Linux, missing cleanup confirmation raises from post-run population before
verification. On Windows, process, pipe and directory cleanup failures are
warnings, independent of execution and evidence integrity. They retain the
failed stage, error category, available process state and absolute owned paths
in Agent logs and metadata, and do not prevent scoring valid evidence. ACP records
them in its summary and Agent context; Host teardown records them in
`agent/cleanup.json`, which CLI and workspace readers project as Trial warnings.
Evidence
write, sealing and manifest failures remain evidence errors. Ordinary prompt
failures may still be verified; cleanup warnings never replace their error.
If Windows execution already failed, post-run evidence recovery records its own
failure in Agent metadata without replacing the original execution exception or
publishing an invalid canonical trajectory.
Unconfirmed native usage is unavailable rather than inferred. Arbitrary external
hard-kill recovery and restoration across rebuilt Hosts are not guaranteed.
One Agent retains a stable private Session state and reuses one call staging
directory. Closed evidence is moved to the current Agent logs before staging
reuse, including on cancellation. Concurrent invocations of that Agent reject
before modifying evidence. Context population preserves caller metadata.
Each accepted invocation clears prior published evidence before validating its
Host. Post-run population admits only that invocation and writes a trajectory
after evidence validation and the platform's cleanup policy. A deleted or replaced Host runtime requires a new
Agent, even when the same Host object is reused.

Failed invocations best-effort retain `agent/trajectory.partial.json`, an atomic,
diagnostic-only ATIF document marked incomplete. ACP recovers the bounded valid
event prefix, including an interrupted gzip stream or final record; malformed
records stop recovery and unrelated Sessions are not joined. It does not fabricate
completion, missing output, usage or timing. Retention failure cannot replace the
execution error, and a new invocation clears previous diagnostics. Verifiers
read only `trajectory.json`; diagnostic recovery never establishes grading evidence.
CLI and workspace readers use the diagnostic trajectory only when the canonical
file is absent, label it incomplete and retain the Trial's native result status.
A corrupt canonical trajectory remains an error rather than triggering fallback.

`HostEnvironment.runtime_directory(name, short_path=True)` allocates a private
short Linux directory independently of TMPDIR, owned and reused by this Host.
It survives `stop(delete=False)` and is removed on `delete=True`; failed removals
retain ownership for retry. RSIversi's XDG runtime is limited to 28 UTF-8 bytes.
`exec_argv` accepts a positive `termination_grace_sec` on Linux; its default
belongs to [`environment`](../../src/psycheval/harbor/environment.py).
Windows uses owned Job termination and rejects a custom grace.
On Linux ACP requests its shutdown budget plus five seconds; cancellation and
Host stop share the same command termination operation.
After forced Linux group termination, Host waits for remaining group members to
exit or become zombies before completing the command or releasing its workspace.
The termination deadline covers leader exit, pipe draining and member settlement,
including after forced termination. Failure to settle within that bounded cleanup
reserve is reported as a cleanup error.
Failed termination remains owned after the command finishes. Subsequent Host stop
retries settlement of the retained process identities and keeps the runtime and
workspace until settlement succeeds; a missing group leader does not clear this
ownership or permit signalling a reused process group.
Stop failures identify the retained owned paths for a later stop retry. Host does
not admit new commands or filesystem operations until that retry succeeds, and
does not delete directories while a process may still use them. Windows retains
the Job handle on failed settlement so a retry can verify all descendants.
Process-table scans
and member-status checks run off the event loop. Host retains members observed
before SIGTERM as well as after SIGKILL, including those that leave the group
during shutdown; inaccessible unrelated process groups are skipped, while an
unreadable retained member cannot confirm settlement.

## Native WorkBuddy ACP

`psycheval.harbor.workbuddy_agent:HostWorkBuddyAgent` runs the desktop-bundled
CodeBuddy CLI on Windows and reports the Agent name `workbuddy`.
Supply explicit absolute `installation_dir`,
`profile_dir` and `auth_file` paths and an exact advertised `model_name`.
`inspect_workbuddy` accepts the same paths and returns version and model
configuration information without submitting a prompt. It creates a temporary,
isolated profile and settles its process tree before returning.

Each Trial copies only the selected desktop model configuration, encrypted
authentication and required product/encryption metadata. The desktop source is
read-only. A bundled Electron Node bootstrap obtains native at-rest material
and supplies the CLI's v1 credential bootstrap through authenticated local pipes.
Before transferring key material, an owned Python helper checks the credential
pipe's server PID against the launched CLI process on the same open handle.
It pins a non-inheritable process handle through the transfer, requires the CLI
to remain alive, and rejects a process born after the helper started.
An identity mismatch fails before any credential bytes are written. Bootstrap
control variables are consumed before launching model-driven tools.
Normal Trials seed only the requested custom model's credentials; inspection
substitutes inert provider-key placeholders and never submits a prompt.
Selection uses the exact advertised ACP ID; custom IDs use `custom-local:` before
the profile's model ID. Built-in model selection seeds no custom provider keys.
Seed reads validate the opened regular
file's identity, links and byte limit before copying admitted bytes.
The bootstrap watchdog uses the configured handshake budget; setup RPCs still
share the harness's single deadline.
Native keys and API credentials are not command arguments or retained evidence.
Missing authentication or unsupported bootstrap capabilities fail before prompting;
the adapter never initiates desktop login or falls back to another CLI or model.
Custom models still require WorkBuddy authentication in ACP mode.

WorkBuddy's cumulative streaming tool-argument updates are retained losslessly.
Its finite stored and decoded evidence budgets are independently configurable;
their defaults belong to the WorkBuddy adapter. The decoded budget does not
increase native usage-history read limits. Exhaustion preserves the prefix,
settles the Job and rejects incomplete tool evidence, as in generic ACP.

The full headless bundle is used, with native session persistence under the
private profile. Every new or restored session confirms its requested model.
Each prompt includes the native workspace root and explains how Task `/workspace`
paths map to it, so native tools can address the prepared files.
Unless overridden through `config_options`, mode defaults to `bypassPermissions`
and multitask defaults to disabled. Harbor Skills
use `CODEBUDDY_SESSION_SKILL_DIRS`; MCP uses ACP session setup. Resume restores
the exact session through advertised resume/load support, excluding replay.

### WorkBuddy usage

New WorkBuddy invocations retain bounded `agent/workbuddy.usage.json` evidence
from the current root Session's native history after process cleanup. This history
belongs to the Agent's isolated runtime profile; desktop chat history is not
copied into it, and a fresh Agent starts with no historical sessions. A pre-call
baseline and the current conversation request identity exclude restored history
and other invocations. Only request identities and numeric usage fields are
retained; message bodies, tool results and credentials are excluded. Source
digests and invocation identity bind the evidence to the current call. Native
history reads share the configured evidence-byte ceiling and the existing
event-line limit. Usage size, history enumeration and line-count ceilings belong
to `harbor.workbuddy_usage`; reaching a limit retains a categorical diagnostic.
Enumeration bounds cover project entries, entries within each project, and total
history files. Exhausting them disables native usage capture for that invocation,
leaving totals unknown without changing execution or scoring. The baseline
retains the enumeration-limit reason; a subsequent invocation tries again.
Unchanged files reuse Agent-local digests bound to file identity, size and
modification time; capture still verifies the selected file's historical prefix.
Baseline hashing has a bounded read budget, independent of the total size of
unchanged history. A file without an admitted baseline digest cannot supply
usage for that invocation. History observation runs outside the event loop and
settles its worker before cancellation returns.

Native model request identity, rather than usage values or notification order,
deduplicates snapshots. Different requests with identical usage count separately.
ACP usage notifications provide identity-based cross-checks, not additional
consumption. Missing identity and conflicting measurements remain diagnostic
evidence without guessed attribution. Repeated snapshots retain known components;
conflicting components remain unknown. Existing Trials are not backfilled.

Prompt tokens include cached input. Cached tokens and cache hit rate measure
cache **reads** only; cache creation is a separate usage component. DeepSeek
`prompt_cache_miss_tokens` does not establish cache creation. Explicit zero is a
measurement, missing values remain unknown, and reasoning tokens are already a
subset of completion tokens. Cache hit rate uses the summed explicit cache reads
over the corresponding inclusive prompt tokens, with measurement coverage.
The CLI SDK's default cache zero, without a provider cache measurement, does not
establish a measured cache miss.

Confirmed native requests populate ATIF and Harbor's input/output/cache context.
Step attribution requires an exact ACP model request identity; confirmed requests
without a matching step remain in Trial accounting without synthetic steps.
Each Trial token field requires complete verified coverage of that field;
uncovered fields remain unknown while verified fields may retain their totals. Usage
collection errors, unsupported formats, conflicts and limits retain categorical
diagnostics without changing execution errors, cleanup or verifier admission.
No collection occurs before cleanup is confirmed. Cost and model timing remain
unknown without their own evidence. The live callback continues forwarding raw
notifications, including repeated usage snapshots.

The `codebuddy` evidence policy validates `codebuddy.ai/toolName` vendor metadata
as canonical identity, rejects identity changes, and interprets business failure
and known raw results. Its vendor metadata checks and open configuration category
labels apply only to this policy. Null optional metadata is treated as absent.
Native `tool_error_code` values `0` and `"0"` mean no tool error. Other
non-null values mark failure; booleans and empty strings are not success codes.
This does not override an ACP failure, nonzero exit code, signal, interruption,
sandbox denial, or explicit business failure.
Display titles do not prove identity; incomplete or failed
commands cannot prove successful execution. Command detection uses the canonical
shell name, ACP execute kind, or native execution fields; renaming a command does
not remove terminal-result checks. Windows cleanup queries an owned Job until
empty within its deadline; missing confirmation produces a warning with owned
paths and does not block valid evidence or verification.
The bundled CLI may announce an active tool again when its arguments resolve.
The WorkBuddy policy merges that snapshot only for the same canonical identity
while the existing call is nonterminal. Reusing a terminal call ID is rejected;
generic ACP still rejects duplicate starts. Every original frame remains retained.
Deferred MCP execution retains its native wrapper identity and arguments. When
the CLI does not emit the underlying invocation as a separate identified call,
tool-name evidence is incomplete; artifact and answer scoring remain available.

Desktop 5.7.7 / CLI 2.156.0 is the initial acceptance baseline. Desktop upgrades
are checked through required files and native bootstrap capabilities.

## Public seams

- `psycheval.harbor.agent:ExternalHarnessAgent` runs a configured external
  process and loads its current-invocation ATIF output.
- `psycheval.harbor.environment:HostEnvironment` executes directly on a trusted
  native host.
- `psycheval.harbor.environment:HostAccessPolicy` describes independent
  filesystem and process permissions for a Host.
- `psycheval.harbor.paths:HostPathMapper` and
  `psycheval.harbor.paths:trial_short_uuid` are the small public seams for
  explicit path translation and workspace naming.
- `psycheval.harbor.hermes:HermesAgent` is the pinned Harbor compatibility
  adapter for current Hermes provider and exact-session behavior.
- `psycheval.harbor.opencode:HostOpenCodeAgent` runs an already installed
  OpenCode CLI through `HostEnvironment` on native Windows or Linux.
- `psycheval.harbor.verifier` implements shared evidence and artifact scoring.
- `psycheval.harbor.datasets` resolves registered flat Harbor Datasets and
  `workbuddy.dataset.v1` bundles without importing Dataset-owned Python code.

## Native OpenCode

For native OpenCode 2 runs, select `HostOpenCodeAgent` by import path, provide
`model_name` as `provider/model`, and install OpenCode on the host first.
Its `executable` kwarg defaults to `opencode`; an optional `version` requires an
exact match. It accepts Harbor's `opencode_config`, `variant`, prompt template,
Skills, MCP servers, and Agent environment. Provider secrets belong in Agent
environment references and OpenCode `{env:NAME}` substitutions, not inline Job
configuration. No user OpenCode configuration or authentication file is copied.
The requested model is registered in the generated provider configuration;
Harbor's configured base URL applies to its OpenAI and Anthropic providers.
Caller `opencode_config` values override these defaults. Configuration sections
that the adapter extends must be objects, and `skills.paths` must be a list of
strings; invalid shapes fail during options preflight and Agent construction.
Task MCP definitions supply defaults for each named server; caller MCP entries
merge over them, preserving options such as authentication, timeout, and an
explicit `enabled=false`. Caller-only servers remain available.
Each Trial owns separate OpenCode home, config, data, state, and cache directories
in neutral runtime storage outside its Agent logs. Execution uses OpenCode's
standalone server so it does not connect to or start the user's managed service.
Stdin forwarding also uses a neutral runtime path, so the launcher command does
not expose a Trial log path.
During setup and execution, generated runtime paths
and OpenCode configuration take precedence over Agent environment overrides,
including Harbor's surrounding execution scope. Other Agent environment values
remain available, and the surrounding scope is restored afterward.
Configuration disables automatic updates, sharing, and
OpenCode's additional Git snapshots (the Environment owns the Task baseline), and
allows task tools by default; callers can override permissions in
`opencode_config`. OpenCode chooses its native tool shell, configurable through
that same object. Instructions arrive on stdin, independent of shell quoting and
Windows command-line length. The `variant` kwarg is passed as `provider/model#variant`.
`HostOpenCodeOptions.websearch_provider` defaults to `"random"`, supplying
`websearch.provider` in the generated configuration to avoid interactive search
setup. Set it to another nonempty provider name or `None` to omit this default;
`opencode_config.websearch.provider` takes precedence.
If the version probe fails or an execution exits nonzero or emits an error event,
the adapter removes `websearch.provider` and retries once, without inspecting the
error text. An empty `websearch` section is removed; other settings are preserved.
The removed setting may come from the adapter default or the caller's
`opencode_config`; caller precedence applies before this fallback.
No retry occurs if that field is already absent, or for cancellation, timeout,
version mismatch, or export/conversion failure following a successful execution.
A failed execution's diagnostic export is best-effort: its failure does not
prevent an already eligible execution retry or trigger a retry by itself.
The fallback applies to
that Agent instance, including later execution and export, without changing caller
options or other Agents. Execution retries reuse the instruction and workspace;
effects of the first attempt are not rolled back.
`opencode-setup.log` retains both probe attempts. On an execution retry,
`opencode-first-attempt.txt`, `opencode-first-attempt.stderr.log`, and any
`opencode-first-attempt-session.json` and
`opencode-first-attempt-export.stderr.log` retain the failed attempt;
`opencode-retry.json` records the fallback. The normal execution logs and exported
Session describe the final attempt; only that successful attempt supplies ATIF.
Native JSON events and stderr stream to Agent logs, including on cancellation.
Execution must emit exactly one Session identity before export. Export failure
or timeout fails the invocation and retains its logs; a previous invocation's
converted trajectory is never reused for a new run.
After a nonzero exit, error event, timeout or cancellation, the adapter attempts
the same bounded export to `opencode-failed-session.json` for diagnosis. Failed
exports fall back to the valid stdout prefix. These sources can supply only
`trajectory.partial.json`, never grading evidence; export errors cannot replace
the original execution failure. Incomplete messages retain their observed content
without synthetic completion or final usage.
After a successful run, `opencode session export --standalone` retains the selected
Session as `opencode-session.json`. Its completed messages, tool results, and usage
are authoritative for ATIF conversion; streamed events alone need not contain
step boundaries. Exported Session and model identities must match the invocation,
and every streamed tool call must occur in the export. Harbor's pinned converter
consumes the normalized message boundaries and produces ATIF. The adapter projects
each completed message's native usage into step metrics and the portable
`model_inference` statistics used by the workbench.
Native model-call duration spans the message's `time.created` to `time.streamed`
(provider response-body end, before tool settlement). It includes client and
network overhead; `time.completed` is the message lifecycle end and cannot
substitute for the model boundary. Tool-call duration spans each call's
`time.ran` to `time.completed`, independently for parallel calls. These native
boundaries use integer milliseconds, preserve zero, and carry distinct model
and tool sources. Missing, invalid, reversed, or nonterminal tool boundaries
remain explicitly unknown with diagnostics; conversion does not invent an
interval from neighboring messages. Model duration lives in step extras, tool
duration only in observation extras, and call extras retain the tool start.
Native timestamps use `event_observed` semantics to disable adjacent-event
estimates. Model-call spans contribute to Model duration, but do not supply
TTFT or decode speed without first-token evidence. Source logs stay unchanged.
OpenCode's `tokens.input`
excludes cache reads and writes; inclusive prompt tokens sum `input`, `cache.read`,
and `cache.write`. Cache hit rate divides cache-read tokens by inclusive prompt
tokens over messages with valid paired measurements. An explicit zero read is a
measured miss; a missing or invalid read remains unknown and contributes neither
numerator nor denominator. An omitted cache-write bucket contributes zero;
an explicitly invalid bucket excludes that message from cache-rate statistics.
Cache writes are retained separately and never count as hits. These statistics
cover completed messages in the exported root Session; they do not infer retries,
child Sessions, TTFT, or decoding speed from message timestamps. Cost and reasoning
token metadata remain available independently.
The adapter writes `trajectory.json` as UTF-8 without a BOM,
preserving non-ASCII characters directly. This adapter supports fresh runs only;
resume and trajectory loading are not supported.
Native tool observations retain OpenCode's completion/error state and shell
exit code, so a completed command with a nonzero exit cannot satisfy a successful
source-observation check.
Malformed tool envelopes, identities, states, or step boundaries fail trajectory
conversion explicitly, retaining native logs. Tool calls must not disappear from
ATIF and thereby bypass required/forbidden-tool checks. Unsupported optional
metadata is ignored; an unknown completion status remains incomplete.
Malformed native Session fields raise categorized OpenCode validation errors;
a recorded completion timestamp of zero remains valid.
The version probe uses the same isolated Trial configuration as execution and
retains `opencode-setup.log`. A probe exceeding its 30-second command timeout
reports that probe failure instead of Harbor's overall Agent setup timeout.

## Task annotations

`difficulty` and `category` are optional nonempty string annotations in
`task.toml`, read only from `[metadata]` through `config.metadata`. Omitted fields
remain absent. The `[task]` section follows Harbor's native schema; these labels
are not read from it or used as fallbacks. The shared Task loader preserves the
original configuration bytes.
These labels do not affect execution or scoring and have no fixed enumeration.

## WorkBuddy Tasks

`prepare_workbuddy_job(config: JobConfig, *, host_settings=None) -> JobConfig`
accepts only a Harbor model, deep-copies it, exports every field, and validates
again. It returns independent configuration without creating files, selecting
Tasks, discovering a workspace, or running Harbor. Harbor owns defaults
(including one attempt, timeout multiplier 1.0, and `jobs/<job_name>`), Task and
Dataset selection, multiple Agents, Job identities, and retained artifacts.
Callers export YAML or pass the result to Harbor directly. Benchmark-specific
attempt and timeout settings belong in caller configuration.

Preparation installs `workbuddy_verifier:WorkBuddyVerifier` unless a conflicting
verifier is explicitly configured. An explicit `HostEnvironment` is adapted to
`workbuddy_environment:WorkBuddyHostEnvironment`; native execution requires
explicit filesystem and process access. Other environments retain their own
execution semantics. Skills, MCP servers, environment references, and artifacts
use Harbor's Task/Agent configuration. No Task name triggers hidden additions.

WorkBuddy Tasks declare the upstream `workbuddy.verifier.v1` CompositeVerifier
contract in an ancestor `dataset.toml` and `metadata.source_case` in `task.toml`.
Dataset IDs and versions are descriptive, not an Office allowlist. Plugins use
`verifier.plugin = "module:function"` or the conventional
`shared/verifier/plugin.py`. The installed WorkBuddy runtime owns registry
construction, preparation/custom verification hooks, scoring, and finalization.
Psycheval owns runtime copies and native path/execution adaptation; source
Datasets remain unchanged, including during plugin loading. Importing the
adapter or registering a Dataset does not import the optional runtime or execute
Dataset Python code. The supported runtime is WorkBuddy 0.1.0 with Harbor 0.24.0;
see the [installation workflow](../user/downstream-vendoring.md#install-the-workbuddy-runtime).

Explicit plugin modules bundled in the Dataset load from the runtime copy in a
private package namespace; relative imports resolve within that copy. Installed
plugin modules use the caller's Python environment.

Verifier environment references resolve at execution through Harbor's environment
helpers. The runtime artifact writer applies Harbor's sensitive-environment
serialization rules to canonical score diagnostics before persistence, without
mutating the plugin's score or rereading score files during cleanup. Plugins own
the contents of files they write directly outside this writer.
In-memory adaptation preserves environment values without applying persistence
redaction. Use environment references in exported Jobs; route completeness is
validated by the selected upstream plugin rather than an Office-only planner.

The Dataset services accept explicit `dataset_id`, `path`, `format`, and
`allow_partial`, returning `ResolvedHarborDataset`. WorkBuddy registration is
read-only. A declared `layout.task_root` selects the contained Task collection;
without it, the supplied path is the Task collection. An ancestor manifest is
accepted. Declared counts are validated when present; `allow_partial=true`
permits missing whole Tasks, but never invalid present Tasks or extra Tasks.
Task text, manifest reads, and declared or conventional archives retain bounded regular-file
checks. Fixed Office helper filenames and workspace archives are not required
by the generic plugin contract.

`compute_official_metrics(job_dir, *, expected_tasks=None)` returns the upstream
metric object for one Harbor Job directory, without writing a summary or
requiring completion. An explicit expected Task list takes precedence; otherwise
Harbor's `lock.json` supplies Task identities. Missing or ambiguous identity is
an error. Missing expected Tasks score zero under the upstream policy. A
short-lived view restores full Task names from retained Trial configuration or
locks for Harbor's truncated Trial directory names. It preserves original score
payloads and leaves retained evidence unchanged. Linked paths and unbounded or
nonregular inputs are rejected at read boundaries. Callers own the trusted Job
directory and prevent concurrent replacement during scoring. A parent containing
nested Jobs is rejected rather than treated as an empty Job. The returned
`run_dir` identifies the caller's Job; it is not a browser-safe projection.
Malformed scorer Task entries and unknown Task aliases raise `WorkBuddyError`.
Identity conflicts compare retained paths with paths and digests with digests;
a missing Trial lock does not turn a known path into a conflicting digest.

## WorkBuddy native execution

`WorkBuddyHostEnvironment` recognizes declared workspace archives and the
conventional `environment/workspace.tar.gz`. Otherwise it uses the regular Host
context. A missing archive is valid when none is declared. Real Docker builds,
Compose services, and incompatible native commands require an appropriate
execution environment; the adapter never treats them as successfully executed.
The recognized inert WorkBuddy Compose metadata may accompany an archive.
Native preparation does not install Task dependencies.

The native Host Python/pytest execution-format adapter recognizes
`workbuddy.office.verifier.v1`, independently of Dataset ID. It executes the
source profile's score/reward snippets and supported pipeline using native argv,
with copied tests as the collection root. Other plugins use their own commands
and platform requirements. Office path and environment adaptation maps
`/logs/artifacts` to the Host's dedicated artifact root, independently of the
parent `/logs` directory. Registry prepare, custom verification, and score
finalization remain available. Unknown rewrite expressions remain unchanged and
produce adaptation diagnostics. Only recognized file-access paths, interpreter
launches, and snapshot ordering are changed; instructions, gold data, and scoring
conditions remain intact. Necessary source/transformed digests remain in the
Trial verifier audit.

On Linux, verifier kwarg `linux_namespace=true` runs non-Office plugin `exec`
and `exec_argv` commands in a Trial-owned mount namespace using preinstalled
Bubblewrap and enabled user namespaces. `/workspace`, `/tests`, `/logs`, `/app`,
and `/tmp` refer to owned paths, including inside Python and browser processes.
The host root remains
readable and networking stays enabled; this is execution-format adaptation under
the existing trusted-host policy. Unsupported namespace setup is a verifier
error. Dataset source and scoring code are unchanged.
Each verification has fresh private `/app`, `/tests`, `/tmp`, and auxiliary
`/logs` storage, removed when verification ends. The Task workspace and Trial
Agent/verifier logs remain shared. Runtime command paths stay logical inside
the namespace; `native_path`, file transfers and directory operations use the
same mount map, including nested test paths. Traversal outside a logical mount
is rejected. Scoped command environment values keep their logical paths.
Host runtime control configuration is unsupported on this wrapper; direct
Python filesystem access remains trusted host access. Each WorkBuddyVerifier
instance admits one verification at a time. Overlapping or
reentrant calls fail before changing its staged Task or environment.

Workspace extraction rejects unsafe paths, links, `.git` metadata, conflicting
duplicate members, and oversized input. Identical repeated entries remain valid.
Tar root directory entries (`.` or `./`) leave the destination's metadata intact.
These filesystem integrity checks are independent of sandboxing. Evaluator-owned
tests and gold files are staged outside the Agent workspace; legitimate project
tests are ordinary workspace content.

## Host configuration

`HostEnvironment` requires an explicit `host_access` policy. In Python this is
`HostAccessPolicy(filesystem=True, process=True)`; Job YAML uses the equivalent
`host_access: {filesystem: true, process: true}` object. Filesystem and process
fields require actual booleans; strings and integers are rejected. These
permissions are independent, although process permission requires filesystem
permission. Filesystem-only Hosts can prepare workspaces, map paths, and move
files, while `exec` and `exec_argv` fail with an explicit process-access error.
The Host is trusted native execution, not a sandbox. It accepts explicit
`workdir_root` and `workspace_source` paths; it does not read the parent
`PEVAL_CONFIG`. The root defaults to `~/workspaces`, resolved internally. Explicit roots must
be native absolute paths; `None`, empty strings, relative paths, and Windows
drive-relative or root-relative paths are errors. Explicit home shorthand must
first be expanded by the caller, for example `Path("~/workspaces").expanduser()`;
the TOML loader performs its own path resolution. `workspace_source` retains
its explicit path resolution rules. Each automatic
workspace is exclusively created as `task_<short UUID>`, using the Trial suffix
when valid. Existing directories are never reused.

`workspace_baseline` is a construction option with values `"git"` (the default)
and `"none"`. Git baseline initialization is performed for owned workspace
contexts and requires `host_access.process=true`; a filesystem-only caller must
choose `workspace_baseline="none"` explicitly. Execution formats requiring
Git diff capture require the Git baseline. The Harbor-compatible `start(force_build)` signature
does not carry this setting.
Owned Task copies exclude inherited `.git` metadata before creating a fresh
baseline; source repositories are never initialized or committed by the Host.

`HostPathMapper(host_os, mappings, task_workdir)` is lifecycle-free and accepts
explicit virtual-to-native mappings. Its `split`, `translate`, and
`translate_environment` methods handle POSIX paths, Windows case-insensitive
and `C:` aliases, traversal checks, and native absolute paths. A native absolute
path that is not a virtual path passes through unchanged. `path_mapper`,
`native_path`, and `work_dir` are available only after successful startup; code
that needs a pre-start mapper constructs `HostPathMapper` directly.

The read-only `work_dir` property equals `native_path(".")`: the native Task
working directory after successful startup. It remains available after
`stop(delete=False)`, but not before startup, after failed startup, or after
deletion. Path mapping, command cwd, runtime configuration, and cleanup share
one workspace record. Startup failure or cancellation waits for outstanding
file operations before removing owned directories. Project copying checks for
cancellation between files and bounded data chunks; WorkBuddy extraction and
Git initialization check between entries or commands. An in-progress filesystem
or Git call must finish before cleanup. Calling `stop` during startup requests
the same cancellation. Copying, extraction, Git commands, and directory deletion
run off the event loop.
Filesystem operations require successful startup. Host-local directory creation,
resetting, type checks, uploads, downloads, and filtered downloads use the native
filesystem directly and do not require `exec`. A non-virtual native absolute path
passed to these operations is used as-is; `host_access.filesystem=true` therefore
grants trusted host filesystem access and is not a confinement boundary. Symlinks
and Windows reparse-point entries are not reported by type checks or copied by
directory uploads or downloads; each traversal reports one warning with the
number of omitted links. Neutral runtime storage rejects linked state
directories. Emptying a linked directory replaces the link without
traversing its target. Relative filesystem paths resolve against the Task workdir.
`ensure_dirs(..., virtual_workdir=True)` explicitly registers Agent-selected
virtual workdirs against the owned workspace; with a borrowed workspace, those
workdirs must lie within its mount target. ExternalHarnessAgent uses this option
for its environment workdir. Ordinary filesystem calls do not register mappings.
Transfers preserve file modes and timestamps; copying a file onto itself or a
hard-link alias leaves it intact. Filters on a mounted directory never erase
excluded source files. Recursive transfers and directory operations run off the
event loop with a bounded number of active filesystem workers per Host. Directory
downloads traverse incrementally. Cancellation and stop signal downloads between
entries and bounded data chunks, discard an incomplete file's temporary copy,
and drain active workers before releasing or deleting the runtime. Completed
files remain at the destination. An operating-system call already in progress
must return before cancellation can finish. Native transfers have no total-size
quota; callers own destination capacity and timeout policy. Process commands
require both successful startup and process permission.
`exec` and `exec_argv` resolve `cwd` through the same
mapper: omitted or relative values use the Task workdir, registered virtual
paths map into their configured directories, and other native absolute paths
are used directly. A missing cwd is created before launch. Passing a native cwd
does not register a transient mapping or transfer ownership; runtime deletion
does not remove that directory. While `stop` is in progress, the Host prevents new
filesystem operations and commands from starting, terminates registered processes,
and waits for their output
callbacks and cleanup before deleting runtime paths. Stop waits for in-flight
launch registration, then drains callbacks without holding the command-launch
lock. Commands waiting to launch recheck the stopping state, including commands
requested by output callbacks. Already running commands may execute concurrently.
Output callbacks must finish
or raise before their command can complete. A callback cannot call `start` or
`stop` on the same Host while its command is active; these calls raise to prevent
waiting on the callback itself. Raise from the callback to abort its command,
then manage the Host lifecycle from the command's caller.
If command cleanup also fails, the original command exception remains primary
and carries the cleanup failures as exception notes. Pending cleanup operations
are drained before the command releases its runtime.
Explicit control commands receive their own runtime JSON, retained until runtime
deletion so their configuration remains available after completion. Runtime JSON writes
run off the event loop; cancellation waits for the write to finish before releasing
the command's runtime. After `stop(delete=False)` completes, commands may run again
in the retained workspace.
Host stop initiates every admitted command's termination before waiting for
completion; one command's grace period does not defer signaling its siblings.
Calling `start` on a successfully started Host is idempotent, including after
`stop(delete=False)`.
`stop(delete=True)`
removes automatic workspaces; external workspace bind mounts are borrowed and
are preserved, including any changes made during preparation or execution.
Task `environment/data/` overlays a borrowed workspace's regular files while
preserving unrelated entries. Links, special files, and file/directory type
collisions remain errors.

`workspace_source` must be an existing, accessible directory, validated during
construction before any workspace allocation. It copies the project into each
independent Trial.
It includes ordinary files, including untracked and Git-ignored files, but
excludes every `.git` entry from both the project and Task environment. Task
`environment/data/` content is then merged into the copy when no preparation
script is present: directories may merge,
but every file or type collision is an error, even for identical files.
Links, Windows junctions, special files, and source/destination overlap are
rejected. The caller must keep source trees and output directories stable
during initialization. No process isolation is implied by copying a project.
With `workspace_baseline="git"`, Git commits the complete merged copy as a
clean initial baseline, including ignored files and empty projects, without
inherited `GIT_*` state or repository hooks. Sources are never modified.
Each baseline Git command has a 30-second timeout; exceeding it fails startup
and cleans up the owned workspace. `workspace_source` cannot be combined with a
workspace bind mount or WorkBuddy archive bootstrap. External workspace bind
mounts are borrowed and are not baseline-initialized. Separate verifier
environments retain their isolated Task test context without copying the project or
initializing a Git baseline.

The explicit `runtime_config.load_host_settings(path)` parser owns
`[harbor.host].workdir_root` in a caller-selected TOML file. Omission uses the
built-in root; empty values are errors. Relative roots resolve against that
TOML file. Job roots take precedence over these settings, then the built-in
default. Prepared Host configurations contain an absolute root.

Native Task test scripts that use Psycheval path mapping select
`psycheval.harbor.verifier.host:HostVerifier` through Harbor's
`verifier.import_path`. It reuses Harbor's script execution and reward loading,
supplying the Host runtime protocol only within verification. The environment
scope is restored on success, failure, and cancellation. It requires a Host;
container scripts retain Harbor's native paths and verifier.

### Native Task input preparation

Ordinary Host Tasks retain Harbor's `environment/` directory, which may contain
only a placeholder. The Host copies only the contents of `environment/data/`
into the Task workdir. Other environment files, including Dockerfiles, are
preparation materials and are neither copied into the workspace nor executed.

An optional `environment/prepare.py` takes full responsibility for input
preparation instead of the default data copy. It must define the synchronous
function `prepare(workdir: str) -> None`. The argument is an existing native
absolute directory. The environment materials are staged outside the workspace;
the function runs in a separate process using the current Python interpreter.
Use `__file__` to locate sibling data and helpers. Dependencies must already be
installed. Task sources are not modified by the framework. Time-dependent
inputs and the reference time needed by verification belong to the Task.
Preparation and verification scripts are trusted Task code with native host
permissions. Their environment retains normal Host/Task settings, including
explicit credentials needed by the Task; it is not a secret-isolation boundary.
Judge-specific `PEVAL_JUDGE_*` settings are excluded from these script children.

Preparation runs after copying `workspace_source`, before the Git baseline and
Agent setup. Repeated starts of a retained Host do not rerun preparation; a new
workspace does. Borrowed workspaces are never baseline-initialized or deleted.
The default copy rejects file collisions; scripts explicitly control their own
workspace changes. Filesystem-only Hosts can copy data, but scripts require
process access. Missing functions, import errors, and execution failures abort
the Trial before the Agent runs. Output is retained in `prepare.log` at the Trial
root. Harbor's environment-start timeout also covers preparation; cancellation
terminates the process tree before removing owned directories.
Combined preparation stdout/stderr is limited to 8 MiB; exceeding the limit
fails preparation and terminates its process tree while retaining the log prefix.

WorkBuddy and separate verifier environments retain their own preparation
contracts and do not invoke this input hook.

The [prepared-files example](../../examples/tasks/native-prepared-files/README.md)
combines static source data, a preparation transform, GT comparison, and weighted
script checks using only the Python standard library.

### Script checks and weighted scoring

The ordinary verifier CLI accepts `grader.json` through the existing `test.sh`
and `test.bat` entrypoints. `custom_checks` declares a list of unique nonempty
check IDs implemented by a sibling `test_outputs.py`. The script and declaration
must either both exist or both be absent. Custom-only configurations do not
require a trajectory. Registration and preview never execute Task code.

The script runs as native Python argv with `--context <path>` and
`--output <path>`. Context uses the runtime JSON protocol's `paths`: `workdir`,
`tests`, `artifacts`, `agent_logs`, and `verifier_logs`. It can read the current
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
`aggregate(checks, *, plan)` computes `sum(weight * passed) / sum(weight)` over
the complete plan. Dimension scores use the same rule; empty dimensions score
one. `evaluate` only evaluates built-in checks and never executes Task code.
Dataset-owned scorers and WorkBuddy scoring retain their own policies.

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
the step name when present, the current deterministic rewards before LLM merging,
referenced artifacts with read metadata and faithful text, and the rubric's
question, pass/fail criteria, and scope limits when present. The default prompt
keeps the `id`, `passed`, `reason` protocol and labels task instructions and Agent
content as untrusted assessment data. Task instruction text is enclosed in
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

`reward.json` contains the final reward, rule dimensions, `rule_score`, and, only
when complete, `llm_score`. `score.json` adds `llm_judge_component_score` only
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
These files are diagnostic, not another score authority. Every invocation removes
previous framework scores, `judge/`,
`artifact_manifest.json`, `artifact_text/`, `raw_artifacts/`, `judge_evidence/`, and the legacy
`judge-evidence/` directory before scripts run, without following links.
Successful results are atomically published with reward last; verifier errors
retain diagnostics without a current reward.
`judge/` is reserved for framework diagnostics and is recreated after custom
scripts finish, without following links.

## Native process execution

Ordinary child commands receive no automatic `PEVAL_CONFIG`. Control components
explicitly request effective runtime configuration through the Host protocol;
external harnesses supply their invocation document, and verifier launchers use
`HostEnvironment.runtime_config_env()`. The generated document contains native
paths, Python, and optional harness protocol version 2 with `run` or `resume`.
Harnesses remove evaluation control variables before launching actual Agents.
Generated runtime directories use neutral names. Agent homes and active state
live outside retained Job/Trial paths; necessary state is collected for diagnostics
and resume. This reduces incidental evaluation clues without concealing
user-supplied paths or providing access isolation.
Command environment overrides are applied to the host process. When a command
overrides `HOME` without explicitly setting `NVM_DIR`, HostEnvironment removes
the inherited host `NVM_DIR` so Node installers cannot accidentally target a
different home; an explicit command `NVM_DIR` remains authoritative.

HostEnvironment supports native Linux and Windows adapters. Windows acceptance
requires the remote Windows CI job; Linux or WSL results do not establish native
Windows behavior.

`HostEnvironment.exec_argv` accepts a nonempty argument sequence and the same
cwd, environment, timeout, and user controls as `exec`. It starts the executable
directly, sharing logging, runtime configuration, and process cleanup with shell
execution. Arguments and explicit per-call `env` values are literal; callers map
their virtual paths explicitly through `native_path`. Task, persistent, and
scoped environment values retain environment-path mapping in both execution
modes. Precedence remains Task < persistent < per-call < scoped environment;
an active scope overrides even a literal per-call value. Arbitrary argument text is never
interpreted as a shell program. `exec` retains the native
host shell contract. Agents may independently use PowerShell or Git Bash.
Command output uses incremental UTF-8 decoding, preserving characters split
across process-output chunks in both returned text and streaming callbacks.

For Windows shell execution, `PATH` and `PYTHONPATH` overrides use native
semicolon-separated entries; each virtual path is mapped independently while
native entries are preserved. The launch gate preserves the rendered cmd
command text without applying executable-argument quoting to it a second time.

Timeouts cover both process completion and draining captured output. Timeout
and cancellation cleanup target the Linux process group or Windows Job even
after the command's parent exits. Windows creates an
unnamed Job Object and assigns a waiting, isolated Python launcher before
allowing it to start the requested argv. Closing the Job terminates remaining
descendants; this also avoids a child-spawn race during assignment. See
[Windows Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects).
The launcher consumes the assignment gate token before forwarding the remaining
stdin stream to the owned child, including ACP protocol frames.
Job ownership ends on successful command completion as well as cancellation or
timeout. Remaining descendants are terminated even if they were deliberately
backgrounded; a Windows exec call does not provide a persistent service lifetime.
Existing Jobs use Windows' [nested Job support](https://learn.microsoft.com/en-us/windows/win32/procthread/nested-jobs).
If assignment is denied by host restrictions, startup fails before the target
command runs and reports the Windows error plus existing Job membership when
it can be queried. The adapter does not request breakaway from the host's Job.
On Linux, successful completion leaves descendants alive if they have closed
the captured output pipes. Callers must manage those processes separately.

Windows virtual roots match without case sensitivity, with or without the `C:`
alias; suffix components retain their letter case. Windows virtual paths reject
embedded drive prefixes and alternate-data-stream
syntax, so joining a suffix cannot discard the mapped native root.

## Harness behavior

ExternalHarnessAgent supplies the instruction on stdin, uses the selected Task
or mounted workspace cwd, removes stale trajectory output before invocation,
and fails on invalid commands, timeout, non-zero exit, missing output, or
malformed ATIF. Resume requires retained native state and cannot silently start
a fresh session.

When Skills are configured, both run and resume append a delimited instruction
to inspect relevant `SKILL.md` files in the effective Skills directory. Host paths
are mapped to native paths; other environments use environment paths. Relative
Skills paths resolve against the effective Task workdir. Without Skills, stdin is
unchanged. This does not extend the runtime JSON protocol or copy Skill contents.

Harness trajectory files are decoded strictly as UTF-8, independent of the
process locale or Python UTF-8 mode. The shared trajectory-validation boundary
reuses Harbor's schema and image-reference checks; relative image paths resolve
from the original trajectory directory. Validation reads the file without
rewriting it or normalizing its contents.
Hermes resumes and exports an exact native session and projects only the current
invocation for step-local scoring.

## Copying into a downstream package

The complete `src/psycheval/harbor` subtree is a relocatable source-copy unit.
Its internal imports stay relative; it needs no other Psycheval modules or
workspace. Namespace changes do not rename `PEVAL_CONFIG`, runtime JSON fields,
schema identifiers, or Agent identities. The caller owns downstream Job and
Task commands; copying source does not rewrite external Dataset scripts.

`src/psycheval/atif.py` is a separate copy unit. It can be renamed, uses only the
standard library, and validates without modifying its input. It also owns
`is_atif_content` and `iso_timestamp_ms`. Recognition helpers detect candidate
ATIF; call `validate_atif_trajectory` for strict validation. Adapter conversion
belongs to `psycheval.conversion` and is outside that copy unit. Harbor's
`Trajectory` model remains available directly from `harbor.models.trajectories`.

Follow [Vendoring Harbor integration downstream](../user/downstream-vendoring.md)
for source layout, dependency and WorkBuddy installation, Job configuration,
and runtime checks.
