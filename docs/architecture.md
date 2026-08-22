# Architecture

Psycheval is one Python distribution and package. `peval` is the installed CLI
name, not a second package or module.

```text
psycheval
├── cli                 -> installed as `peval`
├── adapters, ATIF      -> retained-session conversion
├── report, workspace   -> derived views and user overlays
├── serve, state        -> local evaluation workspace
├── assets              -> committed Web bundle
└── harbor              -> Harbor 0.21 adapters, harness, host, verifier
```

## Module boundaries

The package-level implementation reads retained sessions and Harbor Trial
evidence, converts strict ATIF, and builds reports and workspaces behind the
`psycheval.cli` interface. One internal Harbor Trial loader owns read-only
recognition and projection for both direct CLI paths and workspace mounts;
workspace state owns only discovery, overlays, and derived catalog records.
`psycheval.harbor` is the adapter module for Harbor's Agent, Environment,
trajectory, and verifier seams; it owns host execution, harness integration,
and evidence scoring.

The CLI and Harbor adapter share formats and one `peval.toml`, but not parser
ownership: the CLI reads workspace, adapter, Dataset, and mount fields; Harbor
reads only `[harbor.host]`. Child harnesses receive a generated `peval.json`, not
the user TOML.

## Repository topology

- `src/psycheval/` contains runtime code; Harbor adapters live in its `harbor/`
  subtree.
- `tests/harbor/` and `tests/peval/` are collected by the root pytest project.
- `web/` is the private browser source graph; its committed bundle is written
  to `src/psycheval/assets/`.
- `datasets/` contains maintained Harbor Datasets; `examples/` contains
  authoring examples, not maintained evaluation members.
- `skills/peval/` consumes the public command.

## Dependency direction

Core CLI implementation may consume pinned Harbor interfaces but not
`psycheval.harbor` internals. The two implementations exchange only owned
configuration sections and explicit formats. Tasks invoke the installed
verifier rather than checkout-relative Python paths; documentation and skills
consume public interfaces but runtime code does not depend on them.

## Authority seams

Data authority and mutation rules are defined in
[State and data](reference/state-and-data.md).
