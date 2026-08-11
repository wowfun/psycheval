# psycheval

Harbor-based Agent evaluation, maintained PBench Tasks, and trajectory analysis.

## Projects

- **Psycheval** is the root Python package. It provides Harbor host execution,
  external Agent harnesses, Psychevo trajectory conversion, and evidence-based
  verification.
- **PBench** is maintained under the local `datasets/pbench-v1.0` and
  `datasets/pbench-v1.0-plus` Datasets.
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
  --path datasets/pbench-v1.0/web-search-01 \
  --agent psycheval.harbor.agent:ExternalHarnessAgent \
  --agent-kwarg "command=$PWD/.venv/bin/python -m psycheval.harbor.canned_harness --scenario web-search" \
  --env psycheval.harbor.environment:HostEnvironment \
  --environment-kwarg allow_host_execution=true \
  --jobs-dir .local/jobs \
  --n-concurrent 1 \
  --yes
```

HostEnvironment executes trusted code directly on a native Linux or Windows
host and is not a sandbox. PBench remains Linux-targeted and does not claim
Harbor Windows container support.

## Documentation

- [Documentation index](docs/README.md)
- [Psycheval and Harbor](docs/psycheval/README.md)
- [PBench Dataset](docs/pbench/README.md)
- [peval-py](docs/peval-py/README.md)
- [Specifications](specs/README.md)
