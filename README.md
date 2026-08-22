# Psycheval

Psycheval runs Harbor-compatible evaluations, converts Agent sessions to ATIF,
and inspects evaluation workspaces. Its installed CLI is named `peval`; that is
a short command name, not a Python package namespace.

## Install

Psycheval requires Python 3.12 or newer.
Install the checkout as an editable tool before running the examples:

```console
uv tool install -e .
```

The distribution also installs `psycheval-psychevo-harness` for Harbor's
Psychevo integration.

## Quick start

Initialize a workspace and inspect the command tree:

```console
peval init
peval --help
peval view trajectory --help
peval view tr -p <harbor-trial-dir>
```

## Documentation

Start with the [architecture](docs/architecture.md). Use the
[`peval` guide](docs/user/peval/index.md) for CLI workflows and the
[development guide](docs/development.md) when changing the repository.
