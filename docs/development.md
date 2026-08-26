# Development

Install the frozen Python and Node environments from the repository root:

```console
uv sync --frozen
npm ci
```

Python runtime code lives under `src/psycheval`; all Python behavior tests live
under `tests` and use normal package imports. Browser modules live under
`src/psycheval/assets/web`, ship as authored ESM, and are exercised by the Node
tests under `web` without a generated bundle.

Keep Harbor-specific adapters at the pinned public `0.21.0` seams under
`psycheval.harbor`; package-wide CLI, trajectory, report, and workspace code
lives directly under `psycheval`. Update the owning reference and closest
deterministic test when a stable interface changes.

The `skills/peval` package uses progressive references and helper scripts.
Validate its frontmatter, name, and local references with the repository skill
checker. Follow [Documentation Ownership](AGENTS.md) for docs changes.

Build artifacts belong in `.local/` and are not authority. Never develop against
real profile databases, credentials, provider configuration, or user
workspaces.
