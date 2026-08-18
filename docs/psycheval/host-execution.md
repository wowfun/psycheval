# Host Execution

HostEnvironment runs a trusted Harbor Task as ordinary native Linux or Windows
host subprocesses. It is not a sandbox: the Task, harness, and verifier can
access the caller's filesystem, environment, credentials, and network.

Every run must opt in explicitly:

```text
--environment-kwarg allow_host_execution=true
```

HostEnvironment rejects Docker Compose Tasks, resource requests,
Windows-targeted Tasks on Linux, and forced image builds. In addition to
Harbor's exact Trial-owned log and artifact mounts, it accepts at most one
writable workspace bind. Non-bind, read-only, missing-source, additional, and
reserved-path workspace mounts fail before execution. Those restrictions keep
the supported Harbor subset explicit; they do not provide isolation.

Linux execution uses Bash, POSIX aliases, and process groups. Native Windows
execution uses `cmd.exe`, `C:/app`, `C:/tests`, and `C:/logs/...` aliases, and
terminates process trees with `taskkill /T /F`. Explicit user switching is not
available on Windows. Host paths containing spaces are supported; characters
that cannot be safely embedded in a `cmd.exe` command are rejected.

Task scripts receive portable paths through:

- `PEVAL_CONFIG`, which names a generated effective `peval.json`
- that JSON's `paths` object for workdir, tests, logs, and artifacts
- the current Python executable's directory at the front of `PATH`

The Harbor parent process may use the same variable to select a user-owned TOML
file:

```toml
[harbor.host]
workdir_root = "~/workspaces"
```

With no setting, HostEnvironment uses `~/workspaces`. Each Agent Trial creates
`<workdir_root>/<trial-short-uuid>` exclusively and uses it as the Task
workdir, including for an unbound ExternalHarnessAgent workdir override, so Task
and Job names are absent from the cwd. Set `workdir_root = ""`
to restore a workdir below the Trial's temporary Host control directory. An
explicit `PEVAL_CONFIG` path must name readable TOML; relative config paths are
resolved from the Harbor process cwd. Unknown `[harbor.host]` fields fail, but
other top-level tables are ignored. HostEnvironment never modifies the user
file and does not accept `workdir_root` as an environment kwarg.

For each child process, HostEnvironment overrides `PEVAL_CONFIG` with an
independent, permission-restricted effective JSON containing native paths. It
removes legacy `PSYCHEVAL_*` variables rather than exposing two configuration
interfaces. External harness invocations add protocol version 2 and the
`run|resume` action; verifier and other processes omit that section.

ExternalHarnessAgent accepts `--agent-kwarg workdir=/workspace`. The value is
the environment-side target used for cwd and `paths.workdir`; the host source
remains in Harbor's `--mounts` JSON. A bind takes priority over the automatic
workspace. If it covers the Task workdir, HostEnvironment merges the Task's
`environment/` files into the host directory before execution, overwriting
conflicting files while preserving unrelated files.

Harbor virtual paths supplied as complete environment-variable values are also
mapped into the same resolved host directories. This keeps installed Agents that
set paths such as `XDG_DATA_HOME=/logs/agent/...` inside the Trial on native
hosts. Values that merely contain a virtual path as part of another string are
left unchanged.

Use HostEnvironment only with code you trust. A workspace bind is direct host
state: Agent changes are neither snapshotted nor rolled back, cleanup never
deletes the source, and concurrent Trials sharing it can race. Use Harbor's
isolated environment providers when the Task or harness is untrusted.

An automatic workspace follows Harbor's Environment `delete` setting. With
`--delete`, HostEnvironment removes only the workspace and anonymous control
directory it created; with `--no-delete`, both remain for inspection. It never
deletes `workdir_root`. A shared verifier runs in the Agent environment and sees
the same workspace, while a separate verifier keeps a Trial-temporary workdir.

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
