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

Validate the installed Harbor integration without provider credentials or live
Web access:

```bash
uv run pytest tests/harbor/test_cross_platform_trial.py
```

Run PBench with a real compatible Agent:

```bash
uv run harbor run \
  -p datasets/pbench-v1.0 \
  --env psycheval.harbor.environment:HostEnvironment \
  --environment-kwarg allow_host_execution=true \
  [AGENT OPTIONS]
```

HostEnvironment executes trusted code directly on a native Linux or Windows
host and is not a sandbox. PBench remains Linux-targeted and does not claim
Harbor Windows container support. Repository tests use synthetic trajectories
only to validate framework integration; they are not Agent capability results.

## Documentation

- [Documentation index](docs/README.md)
- [Psycheval and Harbor](docs/psycheval/README.md)
- [PBench Dataset](docs/pbench/README.md)
- [peval-py](docs/peval-py/README.md)
- [Specifications](specs/README.md)
