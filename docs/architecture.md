# Architecture

Psycheval is one Python distribution and package. `peval` is the installed CLI
name, not a second package or module.

```text
psycheval
├── cli                 -> installed as `peval`
├── adapters, ATIF      -> retained-session conversion
├── report, workspace   -> derived views and user overlays
├── serve, state        -> local evaluation workspace and ACP client runtime
├── assets              -> authored Web modules, templates, and styles
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

The serve subtree owns one internal FastAPI application for the bundled browser
UI. `run_serve_command` owns listener selection, the single-process runtime, and
shutdown through Uvicorn; the application borrows that runtime and does not own
its lifecycle. The `/api` interface is not a public integration API and does not
publish interactive API documentation or a generated client contract.

The browser UI is one persistent document. The server renders every page shell
allowed for the current role and the requested route selects the initial page;
the browser application owns later navigation, page activation, and history.
Page adapters load on first activation and keep their DOM and draft state until
the document is unloaded. They consume explicit invalidation domains instead of
using navigation as a data-refresh mechanism. Direct page URLs remain complete
entry points with the same server-side access checks.

`WorkspaceApp` owns the active page and maps the `catalog`, `reports`,
`dataset-registry`, `tasks`, and `assistant-config` invalidation domains to page
adapters. Page adapters do not import one another; shared browser primitives do
not depend on the Home runtime. HTML remains `no-store`, browser modules use
strong ETags, and ECharts is loaded only from the versioned immutable workspace
asset rather than from a browser-side third-party fallback.

The serve-owned ACP seam launches only administrator-configured local child
processes and projects their JSON-RPC session events into browser UI state. It
does not enter the retained-session conversion, report, workspace overlay, or
Harbor evidence paths. ACP conversations remain Agent-owned runtime state; an
explicit, bounded context attachment reads from those existing authorities
without transferring write ownership to the ACP client.

## Repository topology

- `src/psycheval/` contains runtime code; Harbor adapters live in its `harbor/`
  subtree.
- `tests/harbor/` and `tests/peval/` are collected by the root pytest project.
- `src/psycheval/assets/web/` is the browser module graph distributed with the
  package and served directly by the local workspace. `web/` owns its Node test
  harness.
- `datasets/` contains maintained Harbor Datasets; `examples/` contains
  authoring examples, not maintained evaluation members.
- `skills/peval/` consumes the public command.

## Dependency direction

Core CLI implementation may consume pinned Harbor interfaces but not
`psycheval.harbor` internals. The two implementations exchange only owned
configuration sections and explicit formats. Tasks invoke the installed
verifier rather than checkout-relative Python paths; documentation and skills
consume public interfaces but runtime code does not depend on them.

Pydantic models own the validated CLI workspace configuration, HTTP request
shapes, and Problem responses. Large catalog, report, and Harbor projections
remain owned by their domain modules instead of being duplicated as transport
models. Uvicorn is the only production ASGI adapter; integration tests exercise
the same application through a test-owned Uvicorn host.

## Authority seams

Data authority and mutation rules are defined in
[State and data](reference/state-and-data.md).
