# Psycheval

Psycheval is an installable Python package that extends Harbor with a trusted
host Environment, an external-harness Agent, a Psychevo-to-ATIF harness, a
versioned runtime protocol, and evidence-based verification.

## Install

Psycheval requires Python 3.12 and pins the stable Harbor 0.21.0 release:

```bash
uv sync
```

Invoke Harbor directly; there is no `psycheval` wrapper command.

Public integration targets are:

- `psycheval.harbor.environment:HostEnvironment`
- `psycheval.harbor.agent:ExternalHarnessAgent`
- `psycheval-psychevo-harness`

## Installation Validation

Run the repository's generic Harbor integration fixtures after installation:

```bash
uv run pytest tests/harbor/test_cross_platform_trial.py
```

These tests use repository-internal single-step and multi-step synthetic
fixtures to validate Harbor orchestration, paths, resume, artifacts, verifier
execution, and reward behavior. The fixtures are not installed as a command and
their results do not measure Agent quality. PBench Task verifiers are validated
directly from explicit Task-owned fixtures; run PBench with a real compatible
Agent for capability evaluation.

By default, HostEnvironment gives each Agent Trial an anonymous
`~/workspaces/<trial-short-uuid>` workdir. To select another root, point the
Harbor parent process at a user TOML file:

```bash
PEVAL_CONFIG=/path/to/peval.toml uv run harbor run ...
```

```toml
[harbor.host]
workdir_root = "/path/to/workspaces"
```

An empty `workdir_root` restores the temporary Host workdir behavior. The user
TOML is read-only from Psycheval's perspective; child processes receive the
same variable pointing to a generated effective JSON instead.

## External Workspace

Select a writable workspace by binding an existing host directory to an
environment path and passing that target to ExternalHarnessAgent:

```bash
HARBOR_TELEMETRY=0 uv run harbor run \
  --path /path/to/task \
  --agent psycheval.harbor.agent:ExternalHarnessAgent \
  --agent-kwarg "command=/path/to/harness" \
  --agent-kwarg workdir=/workspace \
  --env psycheval.harbor.environment:HostEnvironment \
  --environment-kwarg allow_host_execution=true \
  --mounts '[{"type":"bind","source":"/path/to/repository","target":"/workspace"}]' \
  --n-concurrent 1 \
  --yes
```

`workdir` is the environment-side mount target, not the host source. A Host
workspace bind writes directly to the source directory and survives Trial
cleanup. Do not share one writable source across concurrent Trials.

## Next Steps

- Read [Host Execution](host-execution.md) before using HostEnvironment.
- Read [Harnesses](harnesses.md) to run Psychevo and diagnose a Trial.
- Read the [PBench guide](../pbench/README.md) for Dataset and scoring details.

The normative package contract is
[`specs/100-psycheval`](../../specs/100-psycheval/spec.md).
