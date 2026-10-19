# Psycheval

Psycheval runs Harbor-compatible evaluations, converts Agent sessions to ATIF,
and inspects evaluation workspaces. Its installed CLI is named `peval`; that is
a short command name, not a Python package namespace.

## Install

Psycheval supports Python 3.12–3.14. Install it in a downstream project:

```console
uv add "psycheval==0.1.0rc1"
```

For standalone commands, expose both Psycheval and its Harbor dependency:

```console
uv tool install --python 3.14 --with-executables-from harbor "psycheval==0.1.0rc1"
```

In a project use `uv run peval` and `uv run harbor`; a tool installation exposes
`peval` and `harbor` directly. See the [development guide](docs/development.md)
for editable source installation and the [integration workflow](docs/user/downstream-vendoring.md)
for optional WorkBuddy runtime installation or source copying.

This is a pre-release with no compatibility guarantees; pin an exact version.
Public integration surfaces are the documented [Harbor interfaces](docs/reference/harbor.md),
the standalone ATIF validator, `psycheval.cli.main`, and the
[harness plugin protocol](docs/reference/jobs.md#harness-interface).
Other importable modules and the local browser HTTP API are internal.
The full package installs the dependency constraints declared in
[pyproject.toml](pyproject.toml), including the exact Harbor and ACP versions.

## Quick start

Initialize a workspace and inspect the command tree:

```console
peval init -r .local/evaluation
peval --help
peval view trajectory --help
peval view tr -p <harbor-trial-dir>
```

The first command initializes only workspace state under `.local/evaluation`.
The optional [Agent Skill](skills/peval/SKILL.md) is distributed with the tagged
source, separately from the Python package. Download the source ZIP for the
installed release, extract it, then run
`peval init -r .local/evaluation --skill <source-directory>/skills/peval`.
This explicitly installs or replaces the workspace's Skill. The chart viewer
downloads its pinned ECharts asset on first use and caches it in the workspace.

## Documentation

Start with the [architecture](docs/architecture.md). Use the
[`peval` guide](docs/user/peval/index.md) for CLI workflows and the
[development guide](docs/development.md) when changing the repository.
