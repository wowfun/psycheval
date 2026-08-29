# Development

Install the frozen Python and Node environments from the repository root:

```console
uv sync --frozen
npm ci
```

The Node toolchain follows the sanitizer dependency used by `pretty-aui` and
supports Node.js `^22.22.2`, `^24.15.0`, or `>=26.0.0`.

Python runtime code lives under `src/psycheval`; all Python behavior tests live
under `tests` and use normal package imports. Browser modules live under
`src/psycheval/assets/web`, ship as authored ESM, and are exercised by the Node
tests under `web` without an application bundle. The exception is the immutable
`pretty-aui` standalone distribution under `assets/web/vendor`, which is copied
from the exact npm dependency by `npm run vendor:pretty-aui`; do not edit that
generated subtree directly. Its `LICENSE` and `THIRD_PARTY_LICENSES.txt` files
are part of the immutable distribution and must remain in wheel and frozen
application outputs.

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
