# Workspace Jobs

The Jobs page configures and supervises evaluations. A run is one batch with a
shared selection of registered Tasks and named Agent/Model variants. The
workspace owns configuration, process lifetime and derived views; the harness
owns execution, retries, native artifacts and scoring. Harbor is built in.

## Configuration and registration

`[jobs.defaults.<harness-id>]` in `peval.toml` stores explicitly selected defaults.
Harness defaults are applied first, saved defaults second, and the current draft
last. Starting a run does not save defaults. False, zero and empty values remain
explicit values. Credentials use environment references rather than resolved
secrets. Relative configuration paths are based on the workspace.

`jobs.preferred_harness` stores the administrator's most recent Harness selection
in the new-run form. Changing the selection saves it automatically, independently
of Task, variant and execution defaults. Opening the page restores that choice,
falling back to the first available harness if it is no longer installed or
available. Guest selections affect only their current draft.

Harness selection is disabled while its catalog loads or a composer action is
pending; a catalog failure releases the selector so another harness can be
chosen. Preference writes use the current configuration revision. On a save
conflict, the page refreshes options and reports that the change was not saved;
it does not retry the write automatically. Refreshing options preserves the
current draft, and subsequent saves use the refreshed revision.

Harbor uses the existing Dataset registry. Other installed harnesses receive
their configuration from `[harnesses.<id>]` and expose registered sources through
their catalog. Source discovery does not execute Tasks. Preparation records Task
identities and revisions. Preview is optional: starting directly validates and
prepares the current draft before allocating a run. When a preview is supplied,
launch rejects configuration or Tasks changed since that preview. Editing the
draft clears its preview and allows a direct start with the new values.
Valid native Harbor Tasks do not require Psycheval's optional `[task]` metadata
table. When it is absent, the directory name identifies the Task for browsing.

Variants have independent identities even when Agent and Model names match.
They share the selected Tasks and repeat count. Native retained scores and their
authority remain unchanged; variant grouping is workspace metadata.

## Harness interface

Python entry points in `psycheval.harnesses` provide the public interface owned
by `psycheval.jobs.protocol`. `describe` supplies capabilities and defaults;
`catalog` supplies registered Tasks; `prepare` validates a serializable execution
plan without launching; asynchronous `execute` runs in a worker and responds to
cancellation; `read_results` projects native results without changing them.
Plugins may use native libraries or the worker's managed subprocess facility.
Task and result identifiers are opaque and do not require Harbor layouts.

Plugins are trusted installed code. Optional trajectory and evidence capabilities
are explicit; Harbor provides retained verification files, and other harnesses
can provide ATIF through `trajectory_path`. Unsupported capabilities produce an
empty state. Browser routes
are internal interfaces, not the public plugin contract.
Plugin progress accepts only nonnegative integer Trial counts and a current
Trial label; worker identity, lifecycle and output paths are worker-owned. Native
result records are validated independently. Invalid results have run-local
diagnostics; unavailable or invalid optional ATIF leaves native results readable.
Result extensions must be JSON values: objects with string keys, arrays and
scalar values, nested at most 64 levels. Scores must be finite and representable
as browser numbers. Variant summaries compute means without an overflowing
intermediate sum and never modify the individual native scores.
Harbor re-resolves retained Task identities against the current Dataset registry
before hashing or executing them. Saved absolute paths are not execution authority.

Register a no-argument harness factory with an installed Python distribution:

```toml
[project.entry-points."psycheval.harnesses"]
custom = "custom_eval.workspace:Harness"
```

The factory implements `Harness` in `psycheval.jobs.protocol`. Catalog Task IDs
must be stable and uniquely identify registered inputs. A prepared plan includes
`trial_count` and remains JSON serializable; the plugin owns source revision
validation and its native configuration. `execute` receives the allocated
`output_dir` and calls `control.report` with `trials_total`, `trials_started` and
`trials_completed`. Use `control.subprocess` for CLI harnesses so cancellation
tracks the child process. `read_results` returns stable, Job-local Trial IDs,
Task labels, variant IDs, native states, nullable scores and scoring sources.
It reads only retained outputs and must not execute a grader. Optional ATIF paths
are relative to the Job output directory; linked or escaping paths are rejected.

Advanced fields retain their JSON types. Harbor Job fields belong in execution
settings, and Agent fields belong in a variant's options, for example
`kwargs.temperature` as a number or `env.API_KEY` as the string `${API_KEY}`.
Jobs manages `job_name`, `jobs_dir`, Task inputs and Agent/Model identities;
advanced settings cannot override those fields. The preview shows the effective
native configuration. A launch retains Harbor's generated `job.yaml` in the
control directory. TOML defaults cannot represent JSON null; saving such a value
fails explicitly.

## Lifetime and retained state

Each batch starts in `<workspace>/jobs/YYYY-MM-DD__hh-mm-ss/`, using the local
time at execution start. Trials are directly inside a Harbor Job. Allocation is
exclusive across processes and waits for an available actual second rather than
overwriting a directory or inventing a timestamp suffix.

Control records live in `<workspace>/.peval/jobs/<run-id>/`, separate from native
results. They retain the request, prepared configuration, selection, variant
mapping, progress, logs and worker identity. Starting is idempotent for a request
identifier. The independent worker survives browser and web-server shutdown;
reopening the workbench observes it without starting another evaluation.

### Run logs

Harness stdout and stderr are retained together in `worker.log`. Harnesses may
emit UTF-8 NDJSON: each newline-terminated JSON value is one event, with no
required fields or top-level type. Flush each line for timely display. The Jobs
page polls every two seconds while runs are active and displays each event as
formatted JSON without interpreting severity, timestamps, or lifecycle state.
Warnings and errors are displayed as supplied; logs do not change run outcomes.
Harbor's native output format is unchanged.

The internal log response contains `entries` (each with `format` and display
`text`) and `truncated`. JSON is formatted on the server so browser number
conversion cannot round large integers. Plain text, tracebacks, invalid or
excessively nested JSON, and incomplete line fragments remain readable text.
Both forms use retained-content credential redaction. Reads return the latest
128 KiB window with an explicit notice when earlier bytes were omitted;
incomplete fragments are replaced on the next poll, not accumulated as events.

Log updates preserve other detail controls and follow new content only when the
reader is at the bottom. Scrolling up pauses following; a return-to-latest
control resumes it. The final log remains readable after execution ends.

Each retained record is validated independently. A corrupt record appears as an
invalid run with a diagnostic and cannot start or stop a process; it does not
prevent reading other runs or discovering their results. Output names must be
valid single-component batch timestamps. Missing output mounts yield no Trial
link until discovery can identify the output. Reads reject links, reparse points
and non-regular files, verify the opened file identity, and enforce their byte
limit on the actual read (16 MiB for control JSON, 2 MiB for configuration and
Task text, 128 KiB for the log tail). Coordination contention is a retryable HTTP
409 conflict. Task preparation runs outside the allocation transaction.
Retained JSON rejects non-finite numbers and nesting beyond 64 levels as corrupt
data, including parser recursion failures.

Requests allow at most 1,000 Tasks, 32 variants, 256 KiB of configuration and 32
levels of nesting. Harbor permits at most 100 repeats and 10,000 Trials per run.
Revisions use relative file identities and contents. Credential keys
(including token keys), known environment secrets and recognizable key literals
are redacted; callers must use environment references for all credentials.
These checks do not infer whether arbitrary custom strings are secret.
The same limits apply cumulatively to a preparation request, with shared files
hashed once. A service accepts one preparation at a time; concurrent attempts
receive a retryable conflict. Browser previews require same-origin JSON requests.
Run result pages contain at most 50 Trials; paging never changes native scores.
In narrow layouts, the Task name occupies its own row so scores and Trial links
remain readable alongside long names.
Unavailable managed roots are omitted from discovery without breaking unrelated
sources. Automatic managed-mount discovery is part of starting Jobs, not a new
Dataset registration; explicit mounts take precedence.

Cancellation first gives the harness an opportunity to clean up. Forced cleanup
is restricted to the owned process tree. A stale heartbeat is not completion;
lost workers are reported as interrupted. Process identity includes creation
identity, not just a PID. Completed execution and passing evaluation are separate
states. Missing scores are not zero. Resume and failed-Trial reruns are not part
of this interface.

A valid retained Trial result remains readable when no Agent trajectory was
produced. Its detail shows the native result and an explicit empty trajectory;
damaged or missing result documents retain their diagnostic state.
Display-only trajectory placeholders carry `synthetic: true` and metadata carries
`trajectory_available: false`; they are not valid imported ATIF evidence.

Managed results enter the existing catalog automatically and are deduplicated
against explicit mounts of the same results. Files remain subject to the
existing retained-evidence access limits. Guest and administrator read behavior
is the same, including configuration previews and logs; starting, stopping and
saving defaults or the preferred harness require administrator access. Secrets
are redacted for both.

## Verification

Use the owning [testing guide](../testing.md) to select deterministic checks.
Jobs fixtures exercise both Harbor and an independent harness. Live runs follow
the [evaluation contract](evaluation.md#deterministic-and-live-validation) and
retain the random seed, selected Tasks, configuration, outcomes and source hashes.
