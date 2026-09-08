# Development

Install the frozen Python and Node environments from the repository root:

```console
uv sync --frozen
npm ci
```

The browser test toolchain supports Node.js `^22.22.2`, `^24.15.0`, or `>=26.0.0`.

Python runtime code lives under `src/psycheval`; all Python behavior tests live
under `tests` and use normal package imports. Browser modules live under
`src/psycheval/assets/web`, ship as authored ESM, and are exercised by the Node
tests under `web` without an application bundle. The exception is the immutable
`pretty-aui` standalone distribution under `assets/web/vendor`; do not edit
generated assets directly. To update it, build the owning pretty-aui checkout
and run `npm run vendor:pretty-aui -- /path/to/pretty-aui/dist/standalone`.
Append `--check` to compare that build with the checked-in distribution without
copying. Review the generated diff and run `npm run check` against the vendored
assets. Normal installation and validation use those checked-in assets and do
not require the upstream checkout or a second package archive. Its `LICENSE`
and `THIRD_PARTY_LICENSES.txt` files must remain present.

Keep Harbor-specific adapters at the pinned public `0.21.0` seams under
`psycheval.harbor`; package-wide CLI, trajectory, report, and workspace code
lives directly under `psycheval`. Update the owning reference and closest
deterministic test when a stable interface changes.

The repository-owned `skills/peval` Skill uses progressive references and
assets and is not Python package data. `peval init --skill <skill-dir>` validates
one explicitly selected local Skill and atomically replaces its workspace copy;
plain `peval init` installs nothing. Validate the repository source with the
Skill checker. Follow
[Documentation Ownership](AGENTS.md) for docs changes.

Build artifacts belong in `.local/` and are not authority. Never develop against
real profile databases, credentials, provider configuration, or user
workspaces.
