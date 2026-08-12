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
- The distribution exposes `psycheval-canned-harness` and
  `psycheval-psychevo-harness` console scripts.
- Users invoke Harbor directly. Psycheval does not add a wrapper CLI.
- The Agent remains non-resumable unless a real harness resume protocol is
  specified and implemented end to end.

## HostEnvironment

HostEnvironment is an explicit trusted-host execution mode. Construction fails
unless `allow_host_execution=true` is supplied. It inherits host process access,
including network and potentially credentials, and must not be described as a
sandbox.

Only unique writable mounts rooted in the exact Trial-owned directories are
accepted. Paths are normalized without losing shell token boundaries, including
paths containing whitespace.

HostEnvironment reports the native host OS through `environment.os`. Its private
process adapter owns all OS-specific execution behavior:

- Linux uses Bash, POSIX runtime aliases, and process-group termination.
- Windows uses `cmd.exe`, `C:/...` runtime aliases, and
  `taskkill /PID <pid> /T /F` for process-tree termination.

Both adapters map Harbor's application, tests, logs, and artifact aliases to the
same Trial-owned host directories. This mapping applies both to command paths
and to environment-variable values that are themselves one complete Harbor
virtual path, including descendants such as an Agent's XDG data directory.
Unrelated environment values are preserved. Windows does not emulate POSIX
users and rejects explicit user switching. Unsupported native operating systems
fail at construction.

Linux recognizes only the POSIX virtual roots. It preserves relative `C:` names
and backslashes as ordinary POSIX filename characters, and it rewrites a virtual
root in a Bash command only when the root begins a shell word rather than when it
is a suffix of expressions such as `~/app` or `${HOME}/app`. Windows accepts both
POSIX and `C:/...` or `C:\\...` spellings for Harbor runtime aliases. When a
Windows command begins with a quoted executable, the `cmd.exe /S /C` command
string retains an outer quote layer so `/S` cannot remove the executable's own
quotes.

This native-host support is distinct from Harbor Windows container support. A
Linux-targeted Task can opt into HostEnvironment and ship both verifier entrypoints,
but it is not thereby a Windows container Task and does not require a Windows
container image.

## External Harness Agent

ExternalHarnessAgent launches a configured process, supplies the task and
Trial-owned paths, enforces its timeout and output contract, and returns the ATIF
trajectory written by that process. Invalid commands, timeouts, non-zero exits,
missing output, and malformed ATIF are explicit errors.

ExternalHarnessAgent derives its working directory, instruction path, and log
paths from `EnvironmentPaths.for_os(environment.os)` and declares native Windows
support. Any other Agent is compatible with a Windows HostEnvironment only when
it declares `SUPPORTS_WINDOWS = True` and its implementation does not require
Bash, apt, or tmux.

The public runtime identities remain `psycheval-external-harness`,
`psycheval-host`, and `psycheval-canned`. `PSYCHEVAL_HARBOR_PYTHON` continues to
select the interpreter available inside the Harbor task environment.

## Hermes Compatibility Agent

`HermesAgent` is a thin subclass of Harbor 0.21's installed Hermes Agent. It
adds only the current Hermes-native `xiaomi` provider mapping
(`XIAOMI_API_KEY`) before delegating setup, execution, trajectory conversion,
and identity to Harbor. After execution it replaces Harbor 0.21's bulk
`--source cli` session export with an exact export of the session ID reported by
Hermes, because current active CLI rows are not bulk-export candidates until
they have an `ended_at` value. A missing or malformed session ID is explicit
failure. The compatibility layer MUST NOT copy or replace the upstream Hermes
Agent implementation, expose credentials in Job configuration, or change the
public Agent name from `hermes`. A conflicting future upstream mapping fails
closed instead of being overwritten. Once a valid session identity has been
reported, failure of the post-run exact-session export is a warning rather than
an Agent failure; it may leave native session telemetry unavailable, but it
must not turn completed model work into an errored Trial.

## Psychevo Harness

The Psychevo harness runs `pevo`, projects its typed transcript into ATIF, and
preserves repeated events, tool call arguments, matching observations, source
blocks, and final output. It does not manufacture calls from prose. Harness
failures are distinguished from Agent-scoring failures. Each invocation uses a
Trial-owned Psychevo database below the Agent logs directory so evaluation never
opens or mutates the user's persistent Psychevo state. The retained database and
its runtime trace are same-Trial telemetry available to downstream readers.

## Verifier

The generic verifier implements the evidence and artifact rules in
[015. Agent Evaluation](../015-agent-evaluation/spec.md). It reads Task-owned
grader configuration and Trial-owned evidence without relying on repository
paths.

The shared verifier reads the Agent trajectory directly. Harbor 0.21 regrade,
which requires a separate verifier environment, is outside this interface and is
not enabled by PBench.

## Harbor Compatibility

The supported upstream contract is the stable Harbor `0.21.0` release. Local
code may not depend on APIs observed only after that tag. Anonymous Harbor
telemetry is an upstream runtime policy; Psycheval documents its opt-out and
disables it in tests, but does not silently override the user's global choice.

## Acceptance Criteria

- A built wheel installs without repository source paths and exposes every
  documented import and console script.
- A deterministic external-harness Trial produces ATIF, checks, reward, and
  artifacts through Harbor 0.21.0 on Linux and native Windows hosts.
- The Hermes compatibility Agent delegates to the pinned upstream Agent with
  the native Xiaomi provider registered, exports the exact completed session
  for upstream ATIF conversion, and rejects a conflicting mapping.
- Host execution cannot be enabled accidentally.

## Attachments

- [Testing](testing.md)

## Related Topics

- [001. Repository Architecture](../001-architecture/spec.md)
- [015. Agent Evaluation](../015-agent-evaluation/spec.md)
- [200. PBench](../200-pbench/spec.md)
