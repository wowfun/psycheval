# Host Execution

HostEnvironment runs a trusted Harbor Task as ordinary Linux host subprocesses.
It is not a sandbox: the Task, harness, and verifier can access the caller's
filesystem, environment, credentials, and network.

Every run must opt in explicitly:

```text
--environment-kwarg allow_host_execution=true
```

HostEnvironment rejects Docker Compose Tasks, extra mounts, resource requests,
non-Linux Tasks, and forced image builds. Those restrictions keep the supported
Harbor subset explicit; they do not provide isolation.

Task scripts receive portable paths through:

- `PSYCHEVAL_WORKDIR`
- `PSYCHEVAL_TESTS_DIR`
- `PSYCHEVAL_AGENT_LOGS_DIR`
- `PSYCHEVAL_VERIFIER_LOGS_DIR`
- `PSYCHEVAL_ARTIFACTS_DIR`
- `PSYCHEVAL_HARBOR_PYTHON`

Use HostEnvironment only with code you trust. Use Harbor's isolated environment
providers when the Task or harness is untrusted.

Harbor 0.20.0 enables anonymous telemetry by default. Set
`HARBOR_TELEMETRY=0` when you want to disable it; Psycheval tests always do so
and isolate `XDG_CONFIG_HOME` from the user profile.
