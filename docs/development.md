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
by `npm run vendor:pretty-aui` from the lockfile-pinned package archive in
`web/vendor`; do not edit either generated artifact directly. Refresh that
archive by packing the owning pretty-aui checkout, then update the lockfile,
install it, and run the vendoring command. The lockfile integrity and
byte-for-byte vendor check make a clean `npm ci` reproduce the checked-in
browser distribution. Its `LICENSE` and `THIRD_PARTY_LICENSES.txt` files are
part of that immutable vendored asset and must remain present.

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
