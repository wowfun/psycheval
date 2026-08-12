# Host Execution

HostEnvironment runs a trusted Harbor Task as ordinary native Linux or Windows
host subprocesses. It is not a sandbox: the Task, harness, and verifier can
access the caller's filesystem, environment, credentials, and network.

Every run must opt in explicitly:

```text
--environment-kwarg allow_host_execution=true
```

HostEnvironment rejects Docker Compose Tasks, extra mounts, resource requests,
Windows-targeted Tasks on Linux, and forced image builds. Those restrictions
keep the supported Harbor subset explicit; they do not provide isolation.

Linux execution uses Bash, POSIX aliases, and process groups. Native Windows
execution uses `cmd.exe`, `C:/app`, `C:/tests`, and `C:/logs/...` aliases, and
terminates process trees with `taskkill /T /F`. Explicit user switching is not
available on Windows. Host paths containing spaces are supported; characters
that cannot be safely embedded in a `cmd.exe` command are rejected.

Task scripts receive portable paths through:

- `PSYCHEVAL_WORKDIR`
- `PSYCHEVAL_TESTS_DIR`
- `PSYCHEVAL_AGENT_LOGS_DIR`
- `PSYCHEVAL_VERIFIER_LOGS_DIR`
- `PSYCHEVAL_ARTIFACTS_DIR`
- `PSYCHEVAL_HARBOR_PYTHON`

Harbor virtual paths supplied as complete environment-variable values are also
mapped into the same Trial-owned directories. This keeps installed Agents that
set paths such as `XDG_DATA_HOME=/logs/agent/...` inside the Trial on native
hosts. Values that merely contain a virtual path as part of another string are
left unchanged.

Use HostEnvironment only with code you trust. Use Harbor's isolated environment
providers when the Task or harness is untrusted.

`ExternalHarnessAgent` supports both native operating systems and derives its
paths from `environment.os`. Other Agents are eligible on native Windows only
when they declare `SUPPORTS_WINDOWS = True` and do not depend on Bash, apt, or
tmux.

This is native host execution, not
[Harbor Windows container support](https://www.harborframework.com/docs/tasks/windows-container-support).
PBench Task manifests remain Linux-targeted; when HostEnvironment runs on native
Windows it reports Windows at runtime so Harbor selects `tests/test.bat` instead
of `tests/test.sh`. WSL continues to use the Linux path.

Harbor 0.21.0 enables anonymous telemetry by default. Set
`HARBOR_TELEMETRY=0` when you want to disable it; Psycheval tests always do so
and isolate `XDG_CONFIG_HOME` from the user profile.

The native Windows root suite is the acceptance environment. WSL, Wine, and Git
Bash do not substitute for that run.
