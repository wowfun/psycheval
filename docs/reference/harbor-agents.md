# Harbor Agent Adapters

This reference owns Harbor Agent execution adapters, session conversion, and
native measurement evidence under `psycheval.harbor.agents`. Host configuration,
process execution, Task input preparation, WorkBuddy Tasks, and downstream
copying live in [Harbor integration](harbor.md).

## Host ACP Agent

`psycheval.harbor.agents.acp.agent:HostACPAgent` evaluates a preinstalled ACP v1 Agent
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
are retained. `tool_result_format=acp|rsiversi|codebuddy|dsh` defaults to ACP status semantics;
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
[`acp_protocol`](../../src/psycheval/harbor/agents/acp/protocol.py).
The closed evidence files are bound to an invocation by a summary manifest of
stored and decoded sizes and digests. Bounded streaming readers validate gzip
completion, reject trailing data, and enforce decoded-byte and record limits.
Missing, truncated or substituted retained files fail
conversion explicitly. Publication failures cannot admit partial evidence.
Malformed known protocol data fails explicitly. Context/capacity usage is not
token accounting; absent token and cost evidence remains unknown. Conversion is
performed once by Harbor post-run context population, including partial prompts.
On Windows, a first projection failure propagates as the Trial failure; a repeated
Harbor recovery hook preserves that original exception and diagnostic prefix
instead of aborting the enclosing Job. It never publishes a canonical trajectory
for the failed projection.
Configuration failures do not fabricate a user step.

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
[`HostACPAgent`](../../src/psycheval/harbor/agents/acp/agent.py).
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

`psycheval.harbor.agents.workbuddy:HostWorkBuddyAgent` runs the desktop-bundled
CodeBuddy CLI on Windows and reports the Agent name `workbuddy`.
CLI version identity comes from the native `package.json` version field. The
installation must contain `dist/codebuddy-lite-wb.mjs`; the adapter selects this
bundle through the native launcher and specifies `--acp-transport stdio`.
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
Argument snapshots may arrive before their initial call. Projection buffers a
bounded number and byte volume until a real initial call confirms the same native
tool name and model request ID. Terminal results cannot precede their initial
call, and unresolved or conflicting snapshots fail conversion. Generic ACP does
not accept this ordering extension; no call identities are invented.
Its finite stored and decoded evidence budgets are independently configurable;
their defaults belong to the WorkBuddy adapter. The decoded budget does not
increase native usage-history read limits. Exhaustion preserves the prefix,
settles the Job and rejects incomplete tool evidence, as in generic ACP.

Native sessions persist under the private profile. Every new or restored session
confirms its requested model.
The CLI runs in server mode with explicit stdio ACP and an ephemeral loopback
HTTP listener with native gateway password authentication. The owned process tree
bounds the listener's lifetime. The bootstrap routes native console diagnostics to
stderr before the CLI captures its console, replacing the startup banner with a
constant marker because it contains a generated gateway password. Protocol stdout
remains unmodified NDJSON.
This avoids interpreting the native HTTP startup banner as ACP evidence.
Task prompts are forwarded unchanged. Native tools resolve relative paths against
the ACP Session's working directory, set to the prepared Host workspace.
Unless overridden through `config_options`, mode defaults to `bypassPermissions`
and multitask defaults to disabled. Harbor Skills
use `CODEBUDDY_SESSION_SKILL_DIRS`; MCP uses ACP session setup. Resume restores
the exact session through advertised resume/load support, excluding replay.

### WorkBuddy usage

New WorkBuddy invocations retain bounded `agent/workbuddy.usage.json` evidence
from the current root Session's native history after process cleanup. The adapter
anchors relative Harbor log directories to the working directory at construction.
The usage collector checks its evidence paths for links before reading them.
This history belongs to the Agent's isolated runtime profile; desktop chat history
is not copied into it, and a fresh Agent starts with no historical sessions. A pre-call
baseline and the current conversation request identity exclude restored history
and other invocations. Only request identities and numeric usage fields are
retained; message bodies, tool results and credentials are excluded. Source
digests and invocation identity bind the evidence to the current call. Native
history reads share the configured evidence-byte ceiling and the existing
event-line limit. Usage size, history enumeration and line-count ceilings belong
to `harbor.agents.workbuddy_usage`; reaching a limit retains a categorical diagnostic.
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
Collection exception warnings record the failure stage, exception class name,
and diagnostic code. Unavailable WorkBuddy usage metadata in the trajectory
and Harbor Agent result includes `error_type`. It holds the collection
exception's class name, or null when collection is skipped or usage evidence
fails validation or projection.
Exception messages and tracebacks from the collector stay private.
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
while the existing call is nonterminal. After a terminal result, an explicitly
marked arguments-complete snapshot may repeat the same tool name, model request
and identical arguments. It cannot reopen the call or replace its terminal result;
further lifecycle updates fail. Other terminal-ID reuse and generic ACP duplicate
starts are rejected. Every original frame remains retained.
Deferred MCP execution retains its native wrapper identity and arguments. When
the CLI does not emit the underlying invocation as a separate identified call,
tool-name evidence is incomplete; artifact and answer scoring remain available.

Desktop 5.9.3 / CLI 2.165.0 is the native acceptance baseline. Desktop upgrades
are checked through required files and native bootstrap capabilities.

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
Execution must establish one invocation root before exporting it and verified descendants. Export failure
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
and `cache.write`. Input and supplied cache components must be nonnegative
integers; absent cache buckets use the native zero default. Missing input or
invalid components, including numeric strings, leave the inclusive total unknown.
Known raw components remain in usage evidence. Cache hit rate divides cache-read tokens by inclusive prompt
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

## Native DSH ACP

HostDSHAgent runs a preinstalled `dsh --profile acp` with ordered explicit YAML
patches and an Agent-owned DSH_HOME inside the existing Host runtime. Setup copies
patches once; resume reuses those copies and the exact Session. Setup accepts
at most 16 MiB per patch, opened without following the leaf and checked
against the validated regular-file identity before reading.
New Agent instances get independent state. Host stop(delete=True) owns deletion after process settlement;
delete=False and cleanup failure preserve the existing diagnostic/retry semantics.
There is no recovery after the owning Host runtime is destroyed.
Inherited DSH_/DEEPSEEK_ environment is removed before explicit extra_env; generated
isolation paths win last. Process startup uses the private directory, whereas ACP
Session cwd remains the Task workspace. Raw patches and complete private DSH logs
are not published into Trial evidence; whitelist-only measurement records below
are permitted. Patch provenance retains order and digests, not
contents or environment values. Relative patch resources resolve from the private
startup directory; external resources must use absolute paths.

DSH supports Harbor Skills through the existing `skills_dir` argument. Harbor
prepares Task Skills and merges Job-injected Skills into the effective directory;
the adapter passes its native absolute path directly to DSH's filesystem provider.
Bundle scripts and references retain their original relative paths. The directory
must be readable at setup and before every new or resumed invocation; an absent
or unreadable declared directory fails before the prompt is submitted.

An adapter-owned runtime patch follows every caller patch. It enables the native
Skill registry, filesystem provider and loading tool, sets
`includeDefaultRoots=false`, and replaces `customSkillDirs` with the effective
directory, or an empty list when no Skills were supplied. Default project and
user filesystem roots are never scanned. Other built-in Skill providers remain
under DSH's native configuration. Skill parsing, catalog conflicts and loading
remain DSH-owned; the adapter does not inject Skill bodies into the task prompt.
The generic ACP adapter still requires an explicit subclass Skills capability.
Provenance retains the effective native Skill directories and runtime-patch digest
alongside the existing caller-patch digests, without retaining patch contents.

The DSH wire contract is pinned to deepseek-ai/deepseek-harness commit
`fcc0ad462172522aaf5c93a7b2e01f6b9f0b0159` (0.2.2-rc.1), in
packages/acp/acp/src/{updates,model-control}.ts. DSH messageId identifies assistant
messages; its initial tool title is the original tool name. This vendor-specific
identity mapping does not change generic ACP. Context occupancy is not cumulative
usage. model_name is an exact advertised ACP model ID; model is applied before
reasoning_effort and cannot also appear in config_options.

DSH advertises an empty reasoning-effort choice for provider default. The DSH
wire policy admits that exact native choice; requested assignments remain bounded
and nonempty, and generic ACP continues to reject empty advertised values.

DSH setup probes the executable version before prompting and retains it with patch
digests. Patch validation checks YAML syntax and a sequence root without evaluating
native tagged expressions; DSH owns interpretation of those expressions. Invalid
patch diagnostics omit YAML contents, which may contain credentials.

Tool lifecycle identities must be nonempty before SDK projection. The DSH wire
policy additionally requires nonempty native tool names and messageId on assistant
updates. Malformed model/native output remains failed evidence; conversion never
invents identities to make it gradeable.

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

## Session conversion

Session adapters use frozen ConversionOptions with agent_name, agent_version,
model, max_content_chars, redact, DB mapping, selected adapter options and an
explicit session root. Application configuration owns path expansion and defaults.
The session module publicly exposes finalization, session-context attachment and
ATIF-step metadata projection. Imported ATIF is never repaired.
Hermes resume projects only the current invocation's messages and per-message
usage. Session-wide totals remain available to full-session imports but cannot
supply usage for a resumed subset.
The UTF-8 trajectory reader retains Harbor image-reference checks, including the
pinned version's private image-path hooks.

## Native measurement evidence

Adapters publish versioned `extra.family` with the root ATIF. Family topology
and metric scope follow [state and data](state-and-data.md#session-families-and-metric-scope).
WorkBuddy still rejects ACP frames for unrelated invocation sessions. Vendor
child events in the root envelope require verified native parentage and current
invocation membership before partitioning. They share the root wire budget and
digest manifest. Child conversation ATIF is separate from numeric-only usage
evidence. Child history reads validate containment, identity and baseline.
OpenCode admits one invocation root and separately verified descendants;
descendant export shares a 30-second collection deadline, a 128 MiB retained
export budget and the family member/depth caps. Exhausted budgets or unavailable child
exports retain the admitted prefix, missing-member metadata and diagnostics;
they do not turn a successful root execution into an Agent failure.
The augmented export replaces the original root export atomically. Ordinary
forks and their descendants, including metadata-only descendants, are excluded.
Depth-limited branches retain their
first excluded member as missing without reading its body or deeper descendants.
DB import reads membership and message/part rows
from one read-only SQLite snapshot. Native `session_v2` uses the same export
projection as CLI captures; legacy `session` sources retain their own reader.
Fork metadata is checked before admitting descendants.

Agent adapters own native collection and normalization. Measurement evidence
schema 2 / contract 2 uses `agent/measurements.json` and associated reduced event
files, linked from ATIF extra or AgentContext metadata. The manifest records
invocation/Session identity, installed producer version, per-capability status
(`verified`, `unsupported`, `unavailable`), probe evidence and file digests.
Capabilities require isolated runtime verification; reference symbols alone
are insufficient. A missing capability disables only dependent measurements.
Adapters that populate AgentContext during `run` also publish their canonical
trajectory and usage before returning: Harbor skips its post-run population
callback when the context is already nonempty, including metadata-only contexts.

DSH verifies native Session location/identity, ACP stream retention and flush,
structured tool-result hooks, and availability after normal, cancelled and timed
out runs before Host deletion. Its logical boundary is `step/start` to committed
`assistant/message`, including retries; tools execute afterwards. Native `error`
alone does not establish nonzero shell status. WorkBuddy distinguishes bundled
fields, retained events and readable private records with verified identities.
Phase updates without proven step/retry correspondence cannot supply complete
performance measurements. OpenCode verifies isolated `run --standalone` plugin
loading, incremental HTTP response observation and request/retry/Session linkage.
Its initial protocol support is the MiMo OpenAI-compatible stream. Buffered
responses or unlinked steps leave TTFT/TPS unavailable. Neither ACP notification
gaps nor headless text replace native first-output evidence.
Collection completeness follows retained native settlement events and collection
diagnostics, independently of the execution result. A truncated prefix can still
supply TTFT/TPS samples with proven identities and complete required boundaries;
it cannot supply complete totals. Unsupported response parsing does not invalidate
independently retained native start/completion boundaries.

Only timestamps, event kinds, nonempty flags/lengths, identities, usage, exit
status and digests may be retained. No prompt, body, reasoning, tool output,
authentication header or configuration content is copied. Reduced event evidence
is bounded by 8 MiB and 100,000 records per Trial; the manifest by 64 KiB. Private
reads are streamed, cumulatively bounded by 512 MiB and individually by 16 MiB
per native record, subject to tighter Host/ACP limits. Exhaustion preserves the
prefix/counts/diagnostic and marks truncation; complete totals become unknown.
Observers do not change requests, responses, tool results, permission decisions
or cancellation. Publish after process settlement and before private-directory
deletion: event files first, atomic manifest last. Collection failures never
replace execution exceptions or verifier conclusions. Metric calculation and
value/provenance construction follow the
[measurement contract](state-and-data.md#numeric-metrics).
