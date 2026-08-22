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
