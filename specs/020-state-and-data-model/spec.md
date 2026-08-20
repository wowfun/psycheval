---
name: State and Data Model
---

# State and Data Model

Psycheval distinguishes authoritative evaluation evidence from derived reports
and user-authored workspace overlays.

## Scope

This topic defines authority, identity, derivation, and mutation rules shared by
the runtime, peval-py, and the evaluation workspace. Product-specific wire and
presentation behavior stays in the owning product topic.

## Authority Model

- A Harbor Trial owns its instruction, trajectory, verifier checks, reward,
  exception status, and collected artifacts.
- ATIF is the normalized trajectory representation. Conversion is a projection
  of source evidence, not a license to synthesize missing events.
- peval-py reports are derived from selected source sessions or Trial artifacts.
  They may be regenerated when inputs or presentation rules change.
- Workspace source records, aliases, active/archive state, saved views, attached
  reports, and presentation settings are user-authored overlays.
- Catalog indexes, imported report bodies, render bundles, and query results are
  rebuildable caches unless a more specific specification says otherwise.

A Harbor Trial may be mounted as a linked workspace source. Harbor-owned files
remain read-only and are the sole authority for trajectory, configuration,
resolved inputs, result, reward, and lifecycle facts. peval-py reads those files
directly and derives report metadata in memory; it does not materialize a local
trajectory, metadata, or link-manifest projection. A linked source identity is
derived from its configured mount ID and Job/Trial-relative path so it does not
change when an in-progress Trial later gains a result identifier or evaluation
metadata.

Workspace-authored state for a linked Trial is separate from Harbor evidence and
contains only non-default source presentation state, notes, analysis, and report
bindings. A Trial with no such state has no durable per-source workspace record.
The query catalog may cache derived summaries and source fingerprints, but it is
rebuildable and never becomes an authority for trajectory or evaluation facts.

### Harbor Evidence Projection

For a linked Harbor Trial, peval-py projects the parent Job identity, Trial
identity, Task identity, model provider, complete reward dimensions, phase
timing, and reproduction provenance from the mounted Harbor files. Task names
use result, Trial lock, then Trial config precedence. Job and Trial directory
names remain part of stable source identity even when recorded display names are
available. Explicit model-provider evidence wins over a provider-qualified model
name; an unqualified model never implies a provider.

Task definitions are read only from the Task or Dataset paths explicitly
allowlisted on the matching Harbor mount. A unique lock/config path match wins;
otherwise a unique complete Task package name may match a Dataset's direct
child. Missing, invalid, or ambiguous live metadata never makes an otherwise
valid Trial unreadable and is represented by a diagnostic status.

The recorded Task digest, source, and version are historical Harbor evidence.
The currently mounted `task.toml` description, version, and keywords are live
Task metadata. A live digest mismatch is reported but does not suppress those
fields. A digest carried by a package or Git `ref` remains provenance but is not
compared with a digest computed over the allowlisted local Task directory;
those digests describe different artifact scopes. Parent Job files and resolved
live Task metadata participate in the rebuildable source fingerprint. During
one mount scan, the allowlisted Task index and each selected Task content digest
are computed once and reused across that mount's Trials.

`source_alias` and `source_tags` contain only user-authored overlay values.
Derived presentation uses `display_alias = source_alias or task_name` and
`display_tags = task_keywords + source_tags`, preserving order while removing
case-insensitive duplicates. Category remains an independent user field.

Harbor rewards retain their named dimensions. A numeric `reward` dimension, or
the sole numeric dimension when no `reward` key exists, may be exposed as the
scalar score. Multiple dimensions without `reward` do not produce a synthetic
total and do not enter scalar Reward distributions.

### ATIF and peval-py Sidecar Ownership

Every `trajectory.json` written or exported by peval-py is a complete,
independently exchangeable ATIF-v1.7 document. It is the sole authority for
portable trajectory facts,
including agent identity, ordered steps, messages, tool calls and results,
timestamps, explicit runtime durations and statuses, token accounting, and
portable conversion annotations in the matching ATIF `extra` object.

`trajectory_meta.json` is a peval-py sidecar. It owns import and workspace
context, adapter and data references, aliases, conversion status, failures and
warnings, event and unmapped counts, prompt availability, evaluation state, and
rebuildable presentation values such as active, wall, elapsed, or estimated
durations. Reports, Leaderboard, and Timeline may retain their existing sidecar
shape, but any mirrored trajectory timestamp, duration, or status is projected
from the canonical ATIF document and must not be interpreted independently.
The projection contains exactly one sidecar step for each canonical ATIF step.
It reconstructs steps, tool calls, and observations from canonical nested
identities before merging sidecar-owned presentation or estimated timing data;
equal list lengths never establish identity.
When conversion normalization removes an invalid tool-result reference, the
matching sidecar observation drops that reference as well; the original source
identifier remains only in the canonical result's diagnostic `extra` value.

Conversion output is finalized and strictly validated before it can be written
or projected into a sidecar. Existing ATIF imports are validated without repair.
Validation follows the ATIF-v1.7 content union: an unused text `source` or image
`text` member may be explicitly `null`, but a non-null value is rejected.
An invalid existing artifact remains unchanged and is represented in the
catalog by an explicit ATIF diagnostic. Refreshing a source may produce the
current format; an immutable snapshot is replaced only by an explicit import.

For a linked Harbor Trial, `agent/trajectory.json` remains the trajectory
authority. peval-py accepts canonical ATIF-v1.7 directly. It may also expose an
older ATIF-v1.x Harbor document through an ephemeral v1.7 compatibility view
only when changing the schema label alone makes the complete document pass the
current strict validator; newer-minor documents and any document that requires
field repair remain invalid. The compatibility view is never written back or
persisted as a workspace copy.

Missing aggregate counts may be derived deterministically from canonical steps,
tool calls, and observations. Missing token, cost, active-agent timing, model
timing, and wall timing may be filled from the matching Harbor result or
structurally aligned agent telemetry collected inside the same Trial, including
agent-native databases, session exports, and runtime traces. Supplemental files
are read with the same no-follow containment and bounded consistency guarantees
as the canonical Trial files. Native session identity must align when Harbor and
the adapter preserve the same identifier namespace. When Harbor assigns a
different wrapper session identity, as it does for a Hermes session export,
same-Trial containment plus step source, message, and tool-call alignment is the
identity proof. Late-arriving telemetry is part of the rebuildable source
fingerprint so a subsequent refresh cannot preserve an earlier incomplete
catalog summary.

An exact agent runtime trace wins over a bounded model-boundary estimate. A
boundary estimate is still included in model-duration summaries when no exact
duration exists, but retains its `duration_source` provenance and is never
rewritten as an exact portable trajectory fact. An explicit trajectory value
always wins, supplemental telemetry failure does not invalidate an otherwise
valid trajectory, and derived values remain ephemeral or rebuildable catalog
data. Configuration, lock, result, reward, exception, and lifecycle values must
not overwrite portable trajectory facts.

Absence of `result.json` means the evaluation is still running rather than
invalid. A Trial result with an exception is errored; any other completed result
is completed regardless of reward value. Arbitrary reward dimensions are
preserved and are not averaged into a synthetic score. A Trial without
`agent/trajectory.json` may still expose its authoritative lifecycle diagnostic,
agent identity, model, and result-derived summary in the catalog, but remains
trajectory-unreadable and cannot be opened or exported as a report. peval-py
must not synthesize missing conversation events.

For a stable source session, the trajectory identity is
`{agent.name}:{session_id}`. A conversion without a stable session omits the
optional identity rather than inventing one. Source event time is normalized to
UTC ISO 8601 and its global interpretation is recorded in
`trajectory.extra.timestamp_semantics`.

`metrics.prompt_tokens` is the complete input context, including cache reads
and cache creation. An adapter-provided `input_tokens` value is treated as that
complete total unless the adapter explicitly identifies it as billable-only.
Adapters for billable-only source schemas emit an explicit inclusive
`prompt_tokens` value before entering the common conversion path; the common
path does not infer provider-specific token semantics.
`cached_tokens` is the cache-read subset and may not exceed `prompt_tokens`;
cache creation remains in `metrics.extra`. Billable input and cache buckets are
used to reconstruct the complete total only when no inclusive input total is
available. Step token totals and rankings add prompt and completion only;
cached tokens remain a displayed subset rather than an additional total.

### Model Inference Telemetry

Portable model-inference telemetry uses the versioned
`metrics.extra.model_inference` and `final_metrics.extra.model_inference`
objects. The step and Trial forms retain sufficient statistics rather than
only derived display scalars: summed first-token latency and its sample count,
summed decode duration and its eligible output-token and sample counts, and
cache-covered inclusive prompt tokens, cache-read tokens, and their sample
count. Attempt and successful-attempt counts plus bounded timing and usage
provenance may accompany those values. Trial values are the structural sum of
the aligned step values; equal list lengths never establish that alignment.

TTFT runs from provider request dispatch to the first non-empty token-bearing
text, reasoning, or tool-call delta. Decode duration runs from that delta to
the provider stream's terminal completion. A completed attempt contributes to
TTFT only when both boundaries are exact, and to decode throughput only when
those boundaries and non-negative provider output usage are all exact. Retry
attempts remain distinct. Usage reported by any attempt may contribute to
token and cache accounting even when that attempt does not complete.

The derived Trial values are:

- average TTFT = `ttft_ms_sum / ttft_sample_count`;
- decode TPS = `1000 * decode_token_count / decode_duration_ms`;
- cache hit rate = `cache_read_tokens / cache_prompt_tokens`.

Cross-Trial aggregates use the same ratio-of-sums formulas; they never average
Trial TPS or cache percentages. The cache denominator is the complete inclusive
prompt-token total for attempts with an explicit cache-read measurement,
including an explicit zero. Cache creation is validated as a subset of that
inclusive total and may remain as provenance, but is neither added to nor used
instead of the denominator. A missing cache-read field is unknown and
contributes neither the cache numerator nor denominator, even when cache
creation is present. When a provider payload exposes multiple recognized names
for the same fact, normalization selects the first non-null value; a null alias
does not hide a later value and numeric zero remains present. Missing,
non-finite, negative, zero-denominator, or internally inconsistent evidence
remains absent and diagnostic rather than
being clamped or estimated. Agent, step, generation, and wall duration must
not be relabelled as TTFT or decode duration.

## Identity and Ordering

Source identity must remain stable across pagination, filtering, report
generation, and workspace mutations. Display aliases do not replace source
keys. Event order and repeated occurrences are preserved in trajectories even
when source identifiers repeat.

## Mutations

A mutation reports the state generation it produced or the queued operation that
will produce it. Clients reconcile by generation and stable keys; they do not
assume every mutation returns the entire workspace.

Destructive operations act only on explicitly resolved source keys. Derived
state may be rebuilt, but original inputs and Trial artifacts are not silently
deleted as a side effect of rebuilding a report or catalog.

Deleting a linked Harbor source is not a supported workspace mutation because
the source would be rediscovered and the operation cannot delete Harbor-owned
evidence. Archiving is the reversible way to hide it. If a Harbor Trial becomes
invalid, peval-py reports the current diagnostic and does not serve a retained
last-good trajectory. A missing Trial with no user-authored state disappears;
one retained by source state or a report binding remains as a diagnostic until
the same source identity reappears.

## Related Topics

- [010. Evaluation Lifecycle](../010-evaluation/spec.md)
- [015. Agent Evaluation](../015-agent-evaluation/spec.md)
- [300. peval-py](../300-peval-py/spec.md)
- [310. Evaluation Workspace](../310-eval-workspace/spec.md)
