# Psycheval Testing

## Scope

This attachment defines deterministic validation of the package interface,
Harbor compatibility, harnesses, HostEnvironment, conversion, and verifier.

## Required Coverage

- Unit tests cover command validation, timeout and exit failures, ATIF loading,
  workdir precedence and preparation, user TOML parsing, effective runtime JSON,
  safe dynamic workspace-mount resolution,
  opt-in host execution, Psychevo event projection,
  Trial-owned Psychevo database isolation and exact-session resume, ordered call
  matching, case-sensitive required/forbidden tool-name globs, successful
  observation and process-exit checks, and artifact validation. Artifact coverage includes exact paths,
  safe root-relative globs, multiple matches, missing matches, invalid files,
  and exact references to every matched path in the final answer. External
  harness coverage proves the versioned run/resume action, stale-output removal,
  selected cwd and `PEVAL_CONFIG`, and current-invocation ATIF contract. Host
  coverage proves the default and disabled workdir roots, Trial ShortUUID reuse,
  stale-workspace rejection, multi-step persistence, delete semantics, direct
  workspace writes, Task-context merging, source preservation on stop, and
  fail-fast handling of additional, read-only, missing, reserved, or mismatched
  workspace mounts. Effective-config coverage proves that the parent TOML is
  never modified, child JSON paths are native, generated files are independent,
  and no legacy `PSYCHEVAL_*` variable reaches a child. Hermes coverage proves native capability
  detection, exact-session resume, compressed-session identity updates,
  current-turn projection, and conflicts or missing session identity. A failed
  exact-session export remains non-fatal only for a completed fresh Agent run
  with an independently projectable upstream export; an unrelated export never
  becomes current evidence. Failed Hermes execution cannot leave a prior resume
  marker live. Psychevo failure coverage proves prior NDJSON, stderr, and ATIF
  outputs are removed before state or process validation, session state is
  invalidated until current ATIF succeeds, and no legacy runtime variable
  reaches `pevo`.
- Pure or injected tests cover host-specific command and environment-value path
  conversion, a leading quoted Windows executable, rejection of non-`C:` virtual
  workdirs, user rejection, process-tree termination, and best-effort cleanup of
  every owned root when one deletion fails, without pretending to execute a
  native Windows Trial on Linux, WSL, Wine, or Git Bash.
- Tests assert observable results through the verifier module's public
  `evaluate` and `aggregate` interface rather than Harbor or module internals.
  Module-mode CLI coverage proves that `python -m psycheval.harbor.verifier`
  delegates through the same interface.
- A wheel is built, installed into a clean temporary environment, and checked
  for the documented imports and console scripts.
- Repository-internal single-step and multi-step synthetic harnesses cross the
  complete interface from HostEnvironment and ExternalHarnessAgent through
  ATIF, verifier, reward, and artifact collection. They exercise lifecycle
  behavior only and are not Task or Agent-quality validation.
- A deterministic Harbor CLI Trial passes a workspace through `--mounts` and
  `--agent-kwarg workdir=...`, observes the same writable directory across
  multi-step run/resume invocations, and keeps trajectory and artifacts under
  Harbor's Trial-owned paths.
- A deterministic Harbor CLI Trial supplies an isolated user `peval.toml`, runs
  in `<workdir_root>/<trial-short-uuid>`, reuses that directory across resumed
  steps, and leaves two concurrent Trials in distinct directories. The default
  suite never writes to the real user's home or reads a real user config.
- Deterministic multi-step Trials cover fresh and resumed harness actions,
  persisted workspace and native session state, shared and separate verifier
  modes, step-local evidence and artifact transfer, mean and final rewards,
  `min_reward` early termination, and the archived `steps/<name>` layout.
- `load_trajectory` is rejected before execution for Psycheval Agents because
  neither native nor ATIF load support is declared.
- Tests set `HARBOR_TELEMETRY=0`, isolate `XDG_CONFIG_HOME`, and do not inherit
  user credentials, provider configuration, or persistent state.
  A root autouse fixture owns this process-wide boundary before any
  HostEnvironment subprocess is created. Credential matching includes common
  provider suffixes such as `_API_KEY`, `_API_TOKEN`, and `_ACCESS_TOKEN`.

Live providers and real Web access are not part of the default suite. When run,
their infrastructure failures are reported separately from Agent failures.

The default CI matrix runs the root suite on Linux and a native Windows runner.
Linux verifies that a complete internal fixture Trial selects `test.sh`. Native
Windows verifies that the same generic fixture Task selects `test.bat`, requires
no Bash, handles a Trial path containing whitespace, launches a quoted internal
harness path containing whitespace, and leaves no child process after timeout
or cancellation. The cross-platform fixture Trial also exercises fresh and
resumed multi-step execution; real Psychevo, Hermes, and provider access remain
opt-in.
WSL runs only the Linux Trial and platform-independent Windows adapter tests.
Windows HostEnvironment remains implementation-complete but
native-validation-pending until the native runner succeeds.

## Acceptance Criteria

- Ruff lint and formatting checks pass.
- The root pytest suite passes against Harbor 0.21.0.
- The installed-wheel smoke test passes without a source checkout on
  `PYTHONPATH`, exposes `psycheval-psychevo-harness`, and does not expose a
  synthetic harness console script.
- Native Windows support is called verified only after the Windows Trial passes
  with reward `1` and zero exceptions.

## Related Topics

- [Psycheval](spec.md)
- [015. Agent Evaluation](../015-agent-evaluation/spec.md)
- [200. PBench Testing](../200-pbench/testing.md)
