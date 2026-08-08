# psycheval

Harbor-based Agent evaluation, maintained PBench Tasks, and trajectory analysis.

## Projects

- **Psycheval** is the root Python package. It provides Harbor host execution,
  external Agent harnesses, Psychevo trajectory conversion, and evidence-based
  verification.
- **PBench** is the maintained local Dataset under `datasets/pbench-v1.0`.
- **peval-py** is an independent CLI under `tools/peval-py` for converting,
  inspecting, and comparing retained trajectories.

## Start

Install Psycheval and its pinned Harbor runtime:

```bash
uv sync
```

Run a deterministic PBench Task through Harbor:

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

HostEnvironment executes trusted code directly on a Linux host and is not a
sandbox.

## Documentation

- [Documentation index](docs/README.md)
- [Psycheval and Harbor](docs/psycheval/README.md)
- [PBench Dataset](docs/pbench/README.md)
- [peval-py](docs/peval-py/README.md)
- [Specifications](specs/README.md)
