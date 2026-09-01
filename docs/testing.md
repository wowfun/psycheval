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

## Editable source-tool check

Install the checkout into an isolated tool directory and exercise its public
command entry points:

```console
UV_TOOL_DIR=.local/source-tool \
UV_TOOL_BIN_DIR=.local/source-tool-bin \
uv tool install -e . --force
uv run python scripts/smoke_source_tool.py \
  .local/source-tool-bin/peval skills/peval
```

The smoke covers `peval --help`, default initialization without a Skill,
explicit Agent Skill installation and replacement, and the
`psycheval-psychevo-harness` entry point.
Psycheval does not build or validate wheel, sdist, or frozen executable
artifacts as project gates.

## Platform boundaries

CI runs the complete Python suite on Linux and native Windows. Node,
documentation, skill, and editable source-tool checks run on Ubuntu. Local Linux
or WSL validation does not establish native Windows support; declare it only
after the remote Windows job succeeds.

Live PBench runs are separate opt-in evidence. Classify provider, network,
browser, harness, and upstream failures independently from Agent contract
failures.
