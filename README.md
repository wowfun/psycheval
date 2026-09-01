# Psycheval

Psycheval runs Harbor-compatible evaluations, converts Agent sessions to ATIF,
and inspects evaluation workspaces. Its installed CLI is named `peval`; that is
a short command name, not a Python package namespace.

## Install

Psycheval requires Python 3.12 or newer.
Install the checkout as an editable source tool before running the examples:

```console
uv tool install -e .
```

The editable tool installation also exposes `psycheval-psychevo-harness` for
Harbor's Psychevo integration.

## Quick start

Initialize a workspace and inspect the command tree:

```console
peval init -r .local/evaluation
peval init -r .local/evaluation --skill skills/peval
peval --help
peval view trajectory --help
peval view tr -p <harbor-trial-dir>
```

The first command initializes only workspace state under `.local/evaluation`.
From the checkout root, pass `--skill skills/peval` when that workspace should
explicitly install or replace the repository Agent Skill at
`.local/evaluation/.agents/skills/peval/`.

## Documentation

Start with the [architecture](docs/architecture.md). Use the
[`peval` guide](docs/user/peval/index.md) for CLI workflows and the
[development guide](docs/development.md) when changing the repository.
