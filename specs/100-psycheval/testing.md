# Psycheval Testing

## Scope

This attachment defines deterministic validation of the package interface,
Harbor compatibility, harnesses, HostEnvironment, conversion, and verifier.

## Required Coverage

- Unit tests cover command validation, timeout and exit failures, ATIF loading,
  safe mount resolution, opt-in host execution, Psychevo event projection,
  Trial-owned Psychevo database isolation, ordered call matching, and artifact
  validation.
- Pure or injected tests cover host-specific path conversion, a leading quoted
  Windows executable, user rejection, and process-tree termination without
  pretending to execute a native Windows Trial on Linux, WSL, Wine, or Git Bash.
- Tests assert observable results through public Psycheval interfaces rather
  than Harbor or module internals.
- A wheel is built, installed into a clean temporary environment, and checked
  for the documented imports and console scripts.
- At least one deterministic Harbor Trial crosses the complete interface from
  HostEnvironment and ExternalHarnessAgent through ATIF, verifier, reward, and
  artifact collection.
- Tests set `HARBOR_TELEMETRY=0`, isolate `XDG_CONFIG_HOME`, and do not inherit
  user credentials, provider configuration, or persistent state.
  A root autouse fixture owns this process-wide boundary before any
  HostEnvironment subprocess is created. Credential matching includes common
  provider suffixes such as `_API_KEY`, `_API_TOKEN`, and `_ACCESS_TOKEN`.

Live providers and real Web access are not part of the default suite. When run,
their infrastructure failures are reported separately from Agent failures.

The default CI matrix runs the root suite on Linux and a native Windows runner.
Linux verifies that a complete canned Trial selects `test.sh`. Native Windows
verifies that the same Task selects `test.bat`, requires no Bash, handles a Trial
path containing whitespace, launches a quoted harness entrypoint whose path
contains whitespace, and leaves no child process after timeout or cancellation.
WSL runs only the Linux Trial and platform-independent Windows adapter tests.
Windows HostEnvironment remains implementation-complete but
native-validation-pending until the native runner succeeds.

## Acceptance Criteria

- Ruff lint and formatting checks pass.
- The root pytest suite passes against Harbor 0.21.0.
- The installed-wheel smoke test and deterministic Trial pass without a source
  checkout on `PYTHONPATH`.
- Native Windows support is called verified only after the Windows Trial passes
  with reward `1` and zero exceptions.

## Related Topics

- [Psycheval](spec.md)
- [015. Agent Evaluation](../015-agent-evaluation/spec.md)
- [200. PBench Testing](../200-pbench/testing.md)
