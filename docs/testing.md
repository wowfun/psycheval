# Testing

The root project is the only Python test entrypoint. A complete local gate is:

```console
uv lock --check
uv run ruff check .
uv run ruff format --check .
uv run pytest
npm ci
npx playwright install chromium
npm run check
uv run python scripts/check_docs.py
uv run python scripts/check_skill.py skills/peval
git diff --check
```

Pytest covers Harbor integration and all `peval` CLI behavior in one collection.
Node `check` runs type checking, browser-module tests against the authored ESM
graph, a byte-for-byte check of the vendored `pretty-aui` distribution from the
lockfile-pinned local archive, including its consolidated third-party license
file, and the Chromium visual and browser behavior gate. Deterministic browser
fixtures bind an ephemeral loopback port and expose that origin to their tests;
they do not reserve a repository-wide host port. Live OpenCode ACP coverage
remains an explicit opt-in:

```console
PEVAL_LIVE_OPENCODE=1 npm run test:e2e -- web/e2e/acp-live.spec.mjs
```

Tests isolate HOME/XDG state, config, sockets, timers, and environment secrets.
Focused success is not a release claim unless the expected test inventory is
visible.

## Distribution checks

Build both archives and verify their contents:

```console
uv build --out-dir .local/dist
uv run python scripts/check_distribution_assets.py \
  .local/dist/psycheval-*.whl \
  .local/dist/psycheval-*.tar.gz
uv venv .local/wheel-env
uv pip install --python .local/wheel-env/bin/python \
  .local/dist/psycheval-*.whl
.local/wheel-env/bin/python scripts/smoke_distribution.py
```

Install the wheel in an isolated environment and exercise `peval --help`, shell
completion, a synthetic Harbor Trial view, a fixture-backed conversion and report, plus
`psycheval-psychevo-harness`. The installed environment must not expose removed
module or command names. Build a PyInstaller single file from
`src/psycheval/cli/__main__.py`, collecting both Psycheval and Harbor
package data. Its smoke covers help, a synthetic Harbor Trial view, a
fixture-backed report, and a Dataset Workbench Task scaffold. The PyInstaller
check freezes the checkout source;
wheel provenance is covered separately by the preceding isolated-install smoke.
Both distribution smokes require the pretty-aui license and consolidated
third-party license files; a JavaScript-only asset check is insufficient.

## Platform boundaries

CI runs the complete Python suite on Linux and native Windows. Node,
documentation, skill, and distribution checks run on Ubuntu. Local Linux or WSL
validation does not establish native Windows support; declare it only after the
remote Windows job succeeds.

Live PBench runs are separate opt-in evidence. Classify provider, network,
browser, harness, and upstream failures independently from Agent contract
failures.
