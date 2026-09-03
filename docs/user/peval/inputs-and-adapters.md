# Inputs and Adapters

[简体中文](../../i18n/zh-CN/user/peval/inputs-and-adapters.md)

## Files and ATIF

JSONL accepts one JSON object per line. A line may be a direct message or a
wrapper carrying message, usage, metadata, accounting, and session ordering.
The CLI also reads strict ATIF JSON, supported adapter JSON, Trial cells, and
their contained trajectory artifacts.

## Harbor Trial directories

Use the Harbor Trial root to retain evaluation outcome and provenance alongside
the trajectory:

```console
peval view tr -p <harbor-trial-dir>
```

No adapter selector is required. MultiStepTrial roots produce one source per
Harbor step in result order. Default inspect output can represent a failed or
running step without a trajectory; complete report mode requires every selected
source to have ATIF evidence. Passing `agent/trajectory.json` directly reads
only that ATIF file and does not infer its parent Trial.

## WorkBuddy Office with Harbor

The WorkBuddy Office v1.0 bundle already contains 50 native Harbor Task
directories under `tasks/`; do not convert or copy them. Register the bundle
root on the **Configuration** page, or add a read-only registration to
`peval.toml`:

```toml
[[harbor.datasets]]
id = "workbuddy-office"
path = "/path/to/wb-bench-office-v1.0"
format = "workbuddy.v1"
```

Install the supported external `workbuddy-bench` source revision in the same
environment as Psycheval:

```console
uv pip install --no-deps \
  "workbuddy-bench @ git+https://github.com/Tencent/workbuddy-bench.git@625b2233093ae4f23e76be28c1f341d41cc70373"
```

`--no-deps` preserves Psycheval's Harbor 0.21.0 runtime instead of installing
the benchmark repository's older development pin.

Then create a base Harbor Job file containing exactly one Agent. This example
deliberately opts into Psycheval's trusted Linux host environment and uses
OpenCode:

```yaml
job_name: workbuddy-base
n_concurrent_trials: 1
agents:
  - name: opencode
    model_name: xiaomi-token-plan-cn/mimo-v2.5-pro
environment:
  import_path: psycheval.harbor.environment:HostEnvironment
  kwargs:
    allow_host_execution: true
```

Prepare the isolated two-Job plan, run the commands it prints, and compute the
official aggregate after both Jobs finish:

```console
peval harbor prepare -r .local/evaluation \
  --dataset workbuddy-office --config workbuddy-base.yaml
PEVAL_CONFIG=.local/evaluation/peval.toml harbor run -c <printed-normal-config>
PEVAL_CONFIG=.local/evaluation/peval.toml harbor run -c <printed-special-config>
peval harbor summarize -r .local/evaluation --plan <printed-plan-id>
```

Host execution expands each Task's workspace archive and creates its clean Git
baseline, but it is not a sandbox and does not reproduce container resource or
network isolation. Use it only for trusted Tasks on Linux. A Docker-capable
Harbor environment remains the portable path. The special recruiting Task is
kept in the official denominator even though the source bundle has documented
missing-input, network-contract, and sanity-check defects; preparation prints
those warnings. The **Datasets** page allows browsing this registration but
offers no mutation controls. Trial detail uses `verifier/score.json` as the
WorkBuddy score, retains Harbor reward separately, and exposes only bounded
verifier evidence. See the [Harbor reference](../../reference/harbor.md) for the
exact runtime, verifier LLM, and aggregation contracts.

```console
peval export tr -a opencode -p session.jsonl -o
peval view tr -m raw -p trajectory-opencode-session.json -o
```

Built-in adapter selection is described by the
[CLI reference](../../reference/cli.md). Use `-d @adapter` for a configured
default DB. List and select retained sessions with `--list`,
`--list-interactive`, and repeatable `-s` selectors:

```console
peval view tr -d @opencode --list
peval view tr -m raw -d @hermes -s '#2' -o
```

With several databases, bind adapters and session IDs by one-based DB index:

```console
peval view tr -m raw \
  -d ~/.hermes/state.db \
  -d ~/.local/share/opencode/opencode.db \
  -a d1=hermes -a d2=opencode \
  -s d1=<hermes-id> -s d2=<opencode-id> -o
```

## Custom adapters

An installed distribution registers an adapter in its own `pyproject.toml`:

```toml
[project.entry-points."psycheval.adapters"]
custom = "custom_adapter:CustomAdapter"
```

The adapter implements a supported record, path, or database conversion method;
its exact protocol is owned by source and tests. Put settings under
`[adapters.<id>]` in `peval.toml`.
