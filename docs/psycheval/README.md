# Psycheval

Psycheval is an installable Python package that extends Harbor with a trusted
host Environment, an external-harness Agent, a Psychevo-to-ATIF harness, a
deterministic canned harness, and evidence-based verification.

## Install

Psycheval requires Python 3.12 and pins the stable Harbor 0.20.0 release:

```bash
uv sync
```

Invoke Harbor directly; there is no `psycheval` wrapper command.

Public integration targets are:

- `psycheval.harbor.environment:HostEnvironment`
- `psycheval.harbor.agent:ExternalHarnessAgent`
- `psycheval-canned-harness`
- `psycheval-psychevo-harness`

## Deterministic Trial

Run the PBench Web Search Task with the canned harness:

```bash
HARBOR_TELEMETRY=0 uv run harbor run \
  --path datasets/pbench-v1.0/web-search \
  --agent psycheval.harbor.agent:ExternalHarnessAgent \
  --agent-kwarg "command=$PWD/.venv/bin/python -m psycheval.harbor.canned_harness --scenario web-search" \
  --env psycheval.harbor.environment:HostEnvironment \
  --environment-kwarg allow_host_execution=true \
  --jobs-dir .local/jobs \
  --n-concurrent 1 \
  --yes
```

Use the matching `web-fetch` or `browser-control` Task and canned scenario for
the other deterministic cases.

## Next Steps

- Read [Host Execution](host-execution.md) before using HostEnvironment.
- Read [Harnesses](harnesses.md) to run Psychevo and diagnose a Trial.
- Read the [PBench guide](../pbench/README.md) for Dataset and scoring details.

The normative package contract is
[`specs/100-psycheval`](../../specs/100-psycheval/spec.md).
