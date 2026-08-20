---
name: Psycheval
---

# Psycheval

Psycheval is the root Python distribution that implements Psycheval-owned
extensions at Harbor's Agent, Environment, trajectory, and verifier seams.

## Scope

This topic specifies the installable package, public imports, host execution,
external harness protocol, Psychevo conversion, and generic verifier. It excludes
Dataset-specific instructions and peval-py reporting.

## Distribution and Interface

- The distribution name is `psycheval`, versioned independently from Harbor.
- Python `>=3.12` and the exact stable dependency `harbor==0.21.0` are required.
- Public Harbor integrations live below `psycheval.harbor`.
- Harbor dynamically imports
  `psycheval.harbor.agent:ExternalHarnessAgent` and
  `psycheval.harbor.environment:HostEnvironment`. The pinned Harbor 0.21
  compatibility import `psycheval.harbor.hermes:HermesAgent` retains Hermes's
  upstream runtime identity while enabling its current native Xiaomi provider.
- The distribution exposes the `psycheval-psychevo-harness` console script.
- Users invoke Harbor directly. Psycheval does not add a wrapper CLI.
- ExternalHarnessAgent and HermesAgent implement Harbor's native resume
  lifecycle. Neither claims native or ATIF `load_trajectory` support.

## HostEnvironment

HostEnvironment is an explicit trusted-host execution mode. Construction fails
unless `allow_host_execution=true` is supplied. It inherits host process access,
including network and potentially credentials, and must not be described as a
sandbox.

The optional parent-process `PEVAL_CONFIG` points to a user-owned TOML file.
HostEnvironment reads only `[harbor.host].workdir_root`; omitted configuration
defaults to `~/workspaces`, while an empty string disables the configured root
and retains Trial-temporary workdirs. An explicit config path is expanded and
resolved from the Harbor process cwd and must name a readable regular TOML
file. Unknown keys below `[harbor.host]` fail closed, while unrelated top-level
tables are ignored. The user file is never modified. `workdir_root` is not also
accepted as an Environment kwarg, so this setting has one source.

Without a covering caller workspace bind, each Agent environment maps its
selected workdir to `<workdir_root>/<short-uuid>`; this includes an
ExternalHarnessAgent override that is outside the Task's virtual workdir. The
seven-character suffix is reused from Harbor's generated Trial name when valid;
an explicitly named Trial with no valid suffix receives a new ShortUUID. The
exact directory is created exclusively and a pre-existing target fails rather
than reusing stale state.
Multi-step invocations share the same directory because Harbor retains one
Agent environment. Shared verification uses that environment, while a separate
verifier continues to receive its own Trial-temporary workdir. On stop,
`environment.delete=true` removes only directories created by that Environment;
`delete=false` preserves them. If one owned directory cannot be deleted, cleanup
still attempts every other owned directory and reports the failure. The
configured root and external bind sources are never removed.

Harbor's Agent-log, verifier-log, and artifact mounts remain unique, writable,
and rooted in their exact Trial-owned directories. An Agent environment may
add at most one writable workspace bind. Its source is an existing host
directory and its target is a non-root absolute environment path that does not
overlap `/logs`, `/tests`, or `/solution`. The workspace is direct host state:
Agent writes are not snapshotted, rolled back, or deleted when the Environment
stops. Read-only, non-bind, missing-source, overlapping, and additional
workspace mounts fail before execution. Paths are normalized without losing
shell token boundaries, including paths containing whitespace.

HostEnvironment reports the native host OS through `environment.os`. Its private
process adapter owns all OS-specific execution behavior:

- Linux uses Bash, POSIX runtime aliases, and process-group termination.
- Windows uses `cmd.exe`, `C:/...` runtime aliases, and
  `taskkill /PID <pid> /T /F` for process-tree termination.

Both adapters map Harbor's Task workdir, tests, logs, artifact aliases, and an
optional workspace target to their host directories. Dynamic workspace targets
use longest-prefix matching, so a selected workdir may be the target or one of
its descendants. This mapping applies both to command paths and to
environment-side paths in Psycheval's effective runtime configuration and to
environment-variable values that are themselves one complete Harbor virtual
path, including descendants such as an Agent's XDG data directory. Unrelated
environment values are preserved. Windows does not emulate POSIX users and
rejects explicit user switching. Unsupported native operating systems fail at
construction.

Every Host subprocess receives exactly one Psycheval runtime locator,
`PEVAL_CONFIG`. The parent-process value, when present, names the user TOML;
the child-process value instead names a generated, permission-restricted
`peval.json` in the Environment's anonymous control directory. The effective
JSON has `schema_version=1`, native `paths` for workdir, tests, Agent logs,
verifier logs, and artifacts, and the current Python executable. External
Harness invocations additionally carry `harbor.harness.protocol_version=2` and
`action=run|resume`. HostEnvironment removes every legacy `PSYCHEVAL_*` name
from child environments and prepends the current Python executable directory
to `PATH`. Effective files are unique per execution, do not modify the user
TOML, and follow the Environment's delete lifecycle.

Linux recognizes only the POSIX virtual roots. It preserves relative `C:` names
and backslashes as ordinary POSIX filename characters, and it rewrites a virtual
root in a Bash command only when the root begins a shell word rather than when it
is a suffix of expressions such as `~/app` or `${HOME}/app`. Windows accepts both
POSIX and `C:/...` or `C:\\...` spellings for Harbor runtime aliases. When a
Windows command begins with a quoted executable, the `cmd.exe /S /C` command
string retains an outer quote layer so `/S` cannot remove the executable's own
quotes. Windows environment paths use Harbor's `C:` virtual drive; an explicit
workdir on another drive is rejected by the Agent before environment setup.

This native-host support is distinct from Harbor Windows container support. A
Linux-targeted Task can opt into HostEnvironment and ship both verifier entrypoints,
but it is not thereby a Windows container Task and does not require a Windows
container image.

For a Harbor separate verifier, HostEnvironment recognizes the verifier-only
Trial mount set and materializes Harbor's selected tests build context at the
native `/tests` alias, matching the image contract that the verifier entrypoint
already exists there. Its reconstructed `/logs/agent` and `/logs/artifacts`
trees are verifier-local temporary directories, while `/logs/verifier` remains
the Trial-owned output mount; this preserves the same isolation as a separate
container and prevents artifact upload from mutating the collection source.
Agent environments materialize their build context at the configured Task
workdir, defaulting to `/app`. An unbound ExternalHarnessAgent override resolves
to that same materialized automatic workspace. When a workspace bind covers
the workdir, HostEnvironment merges the Task `environment/` tree into the real
host workspace once before Agent execution: conflicting files are overwritten
and unrelated workspace files are preserved. A staging failure aborts
execution.

## External Harness Agent

ExternalHarnessAgent launches a configured process, supplies the task and
Trial-owned paths, enforces its timeout and output contract, and returns the ATIF
trajectory written by that process. Invalid commands, timeouts, non-zero exits,
missing output, and malformed ATIF are explicit errors.

Its optional `workdir` parameter is an environment-internal path, normally the
target of Harbor's `--mounts` bind rather than its host source. Resolution order
is the explicit Agent `workdir`, the Task's `[environment].workdir`, then the
target-OS `/app` default. The selected path must be absolute and must not be
empty, contain NUL, or traverse a parent. It is created when missing. If a Host
workspace bind is present, the selected workdir must equal its target or be a
descendant. The harness process runs with that cwd; its effective runtime JSON
contains the resolved workdir.

ExternalHarnessAgent derives its working directory, instruction path, and log
paths from `EnvironmentPaths.for_os(environment.os)` and declares native Windows
support. Any other Agent is compatible with a Windows HostEnvironment only when
it declares `SUPPORTS_WINDOWS = True` and its implementation does not require
Bash, apt, or tmux.

Every invocation supplies protocol version 2 and `run|resume` through the JSON
named by `PEVAL_CONFIG`; the Task instruction remains stdin. The canonical JSON
uses environment-side paths so non-Host Harbor Environments can consume it
directly, while HostEnvironment materializes a native translated copy before
execution. A resumable harness stores its native session state below the
configured Agent logs path; a resume without valid state is an error and must
not fall back to a fresh session. Before invoking the command the Agent removes
any previous `trajectory.json`, and the command must create a valid ATIF
trajectory containing only the current invocation's evidence. Harbor preserves
the live Agent logs directory only when the following step resumes it.

The bundled Psychevo module and console entrypoint is a harness command, not a
standalone user CLI. It requires the effective `PEVAL_CONFIG` supplied by
ExternalHarnessAgent and is documented as a value for its `command` parameter.
Synthetic harnesses are repository-internal test fixtures and are not installed
package interfaces.

The public runtime identities remain `psycheval-external-harness` and
`psycheval-host`. The effective JSON's
`executables.python` selects the interpreter available inside a Host task
environment; test wrappers resolve that interpreter from HostEnvironment's
prepended `PATH`.

## Hermes Compatibility Agent

`HermesAgent` is a compatibility subclass of Harbor 0.21's installed Hermes
Agent. It adds the current Hermes-native `xiaomi` provider mapping
(`XIAOMI_API_KEY`) while retaining upstream setup, fresh execution, conversion,
and identity. After execution it replaces Harbor 0.21's bulk
`--source cli` session export with an exact export of the session ID reported by
Hermes, because current active CLI rows are not bulk-export candidates until
they have an `ended_at` value. A missing or malformed session ID is explicit
failure. The compatibility layer MUST NOT copy or replace the upstream fresh-run
implementation, expose credentials in Job configuration, or change the public
Agent name from `hermes`. A conflicting future upstream mapping fails closed
instead of being overwritten.

Hermes stores the exact last reported native session ID in the live Agent logs
directory. Resume requires that marker and may adopt a new reported ID after
native compression. Setup follows the selected Hermes ref
(including its default `main`) but fails before model execution unless the
installed CLI exposes exact resume and session-export capabilities. The complete
native export remains telemetry; `trajectory.json` is projected from the final
user-message occurrence exactly matching the current rendered instruction, so
only the current invocation is scored. A missing projection boundary or failed
exact export is fatal for a resumed step. For a fresh run, once a valid session
identity has been reported, the exact-export command failing remains a warning;
grading still requires the upstream bulk export to contain a projectable
current-instruction boundary. An absent or unrelated export is never converted
into fabricated or cross-session evidence. Before a native invocation can
mutate session state, Hermes invalidates the prior resume marker and publishes a
replacement only after the invocation has established a usable exact session;
a failed fresh or resumed invocation therefore cannot authorize a later resume
against stale state.

## Psychevo Harness

The Psychevo harness runs `pevo`, projects its typed transcript into ATIF, and
preserves repeated events, tool call arguments, matching observations, source
blocks, and final output. It does not manufacture calls from prose. Harness
failures are distinguished from Agent-scoring failures. Each invocation uses a
Trial-owned Psychevo database below the Agent logs directory so evaluation never
opens or mutates the user's persistent Psychevo state. The retained database and
its runtime trace are same-Trial telemetry available to downstream readers. On
the first invocation the harness records the exact completed `threadId`; resume
requires that marker and database, passes the exact ID through `pevo run
--session`, and rejects session drift. Each NDJSON file and projected ATIF
trajectory contains only the current turn. At invocation start the harness
removes the prior invocation's NDJSON, stderr, and trajectory outputs, so an
early state, provider, or conversion failure cannot leave stale gradeable
evidence. After reading any required resume marker, it invalidates that marker
before invoking `pevo` and writes a replacement only after current-turn ATIF
validation succeeds. The `pevo` child receives its Trial-owned database path but
neither `PEVAL_CONFIG` nor any legacy `PSYCHEVAL_*` runtime variable.

## Model Inference Telemetry

Psycheval owns one inference-telemetry module that normalizes Agent-native
observations, validates their presence and token invariants, projects them into
the canonical ATIF extension defined by
[020. Model Inference Telemetry](../020-state-and-data-model/spec.md#model-inference-telemetry),
and fills Harbor's token context from a validated trajectory. Agent adapters do
not duplicate aggregation rules.

ExternalHarnessAgent accepts exact telemetry already present in canonical ATIF
and fills inclusive input, cache-read, and output context without manufacturing
timing. Psychevo projects current-invocation typed usage and accounting, using
native identifiers and trace boundaries rather than positional matching.
Hermes exports the exact current native session after run or resume and parses
that session's structured request usage during post-run context population.
Optional telemetry failure does not invalidate an otherwise valid trajectory.

The current Psychevo compact trace and Hermes session export do not expose a
first-token event. Their generation durations may retain explicit provenance
but must not populate TTFT or decode TPS. Those values remain absent until an
exact producer-owned first-token boundary is available; no estimate is emitted.

## Verifier

`psycheval.harbor.verifier` is a package module implementing the evidence and
artifact rules in [015. Agent Evaluation](../015-agent-evaluation/spec.md). Its
public Python interface is `evaluate(trajectory, config, artifacts_dir)`, which
returns structured checks, and `aggregate(checks)`, which returns Harbor reward
dimensions. The module-mode CLI remains `python -m psycheval.harbor.verifier`
and is an adapter over that same interface. Earlier function names are not part
of the interface.

The module reads Task-owned grader configuration and Trial-owned evidence
without relying on repository paths. Its required-call matcher owns tool-name
glob matching, ordered same-call argument and observation evidence, and
successful process-exit semantics. Its required-artifact resolver safely
expands root-relative POSIX globs once for both artifact validity and
final-answer path checks. Dataset-specific verifiers call `evaluate` with their
generic configuration projection instead of duplicating those rules.

The shared verifier reads the current Agent trajectory directly. A separate
step verifier receives the same file only when the Task declares
`/logs/agent/trajectory.json` as a step artifact. The verifier never reads
archived sibling steps or aggregates step rewards. Harbor 0.21 regrade is outside
this interface and is not enabled by PBench.

## Harbor Compatibility

The supported upstream contract is the stable Harbor `0.21.0` release. Local
code may not depend on APIs observed only after that tag. Anonymous Harbor
telemetry is an upstream runtime policy; Psycheval documents its opt-out and
disables it in tests, but does not silently override the user's global choice.

## Acceptance Criteria

- A built wheel installs without repository source paths and exposes every
  documented import and console script.
- Repository-internal synthetic single-step and multi-step fixtures produce
  ATIF, checks, reward, and artifacts through Harbor 0.21.0 on Linux and native
  Windows hosts without becoming installed package interfaces.
- A deterministic external-harness Trial accepts one Harbor workspace bind,
  runs in the selected target, writes through to its host source, and leaves the
  external directory intact after cleanup. Concurrent Trials are not permitted
  to share that writable source in acceptance coverage.
- Deterministic fresh and resumed multi-step Trials preserve Harbor's workspace
  lifecycle, expose step-local ATIF and artifacts, and produce Harbor-owned
  per-step and aggregate results without evidence leaking between steps.
- The Hermes compatibility Agent delegates fresh execution to Harbor 0.21's
  upstream Agent implementation with
  the native Xiaomi provider registered, resumes an exact native session,
  projects the current turn for scoring, and rejects missing capabilities or a
  conflicting mapping.
- Host execution cannot be enabled accidentally.

## Attachments

- [Testing](testing.md)

## Related Topics

- [001. Repository Architecture](../001-architecture/spec.md)
- [015. Agent Evaluation](../015-agent-evaluation/spec.md)
- [200. PBench](../200-pbench/spec.md)
