# Harbor Integration

Psycheval supports the public Harbor `0.21.0` contract through
`psycheval.harbor`.

## Public seams

- `psycheval.harbor.agent:ExternalHarnessAgent` runs a configured external
  process and loads its current-invocation ATIF output.
- `psycheval.harbor.environment:HostEnvironment` executes directly on a trusted
  native host.
- `psycheval.harbor.hermes:HermesAgent` is the pinned Harbor compatibility
  adapter for current Hermes provider and exact-session behavior.
- `psycheval-psychevo-harness` is the external-harness command for Psychevo.
- `psycheval.harbor.verifier` implements shared evidence and artifact scoring.

## Host configuration

Host execution is opt-in with `allow_host_execution=true` and is not a sandbox.
The parent `PEVAL_CONFIG` may name a user `peval.toml`; Harbor reads only
`[harbor.host].workdir_root`. Omission defaults to `~/workspaces`, while an
empty string keeps Trial-temporary workdirs. Unknown host fields fail closed and
the user file is never modified.

Each child process receives `PEVAL_CONFIG` pointing to a permission-restricted
effective `peval.json`. That runtime document contains native paths, the Python
executable, and, for external harnesses, protocol version 2 with `run` or
`resume`. The user TOML and effective JSON are different interfaces despite
sharing the environment-variable locator at different process boundaries.

HostEnvironment supports native Linux and Windows adapters. Windows acceptance
requires the remote Windows CI job; Linux or WSL results do not establish native
Windows behavior.

## Harness behavior

ExternalHarnessAgent supplies the instruction on stdin, uses the selected Task
or mounted workspace cwd, removes stale trajectory output before invocation,
and fails on invalid commands, timeout, non-zero exit, missing output, or
malformed ATIF. Resume requires retained native state and cannot silently start
a fresh session.

Psychevo state is Trial-owned under Agent logs, so evaluation does not open the
user's persistent database. Hermes likewise resumes and exports an exact native
session. Both project only the current invocation for step-local scoring.
