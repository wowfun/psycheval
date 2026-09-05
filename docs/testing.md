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

## Downstream source-copy checks

The Python suite copies the complete Harbor subtree into an unrelated nested
package and blocks imports of the original `psycheval` package. It exercises
module discovery, verifier and harness entry points, synthetic host run/resume,
and WorkBuddy planning and summarization with local fixtures. Copied production
source is never rewritten. These tests also verify that library calls do not
discover or mutate workspace configuration or print CLI output. Module discovery
also blocks the optional WorkBuddy runtime to verify import-time independence.

Native Office execution tests use owned Task fixtures and the pinned Office
execution wrapper. Linux differential tests compare its Bash path against the
native argv path for passing, failing, empty, skipped, and collection-error
results. Other fixtures cover optional scorers, postprocessing failures, missing
JUnit, runtime-copy audits, and source immutability.

The rule fixture comes from
`wb-bench-office-v1.0/shared/verifier/rule.py`, with an explanatory comment added.
The native profile identifies that source by the SHA-256 of its Python AST,
excluding source positions. To check a local bundle's rule:

```console
uv run python -c "import ast, hashlib, pathlib, sys; source = pathlib.Path(sys.argv[1]).read_bytes().decode('utf-8-sig'); print(hashlib.sha256(ast.dump(ast.parse(source), include_attributes=False).encode('utf-8')).hexdigest())" /path/to/wb-bench-office-v1.0/shared/verifier/rule.py
```

Compare the result with `_RULE_AST_SHA256` in
`src/psycheval/harbor/workbuddy_verifier.py`. Comments and formatting outside
string values do not change this identity. Changes inside the embedded shell
template do. Updating the supported profile requires reviewing execution and
scoring semantics; do not refresh the digest just to make a check pass.
The local Office test below exercises each Task's actual command and graders,
including this rule check; the owned fixture alone does not establish bundle
compatibility.

The real WorkBuddy runtime integration is explicit and uses no provider or live
Dataset service. Install the pinned runtime using the
[installation workflow](user/downstream-vendoring.md#install-the-workbuddy-runtime),
then run:

```console
PEVAL_WORKBUDDY_RUNTIME_TESTS=1 uv run --no-sync pytest tests/harbor/test_workbuddy_verifier.py tests/harbor/test_vendoring.py -k real_runtime
```

On PowerShell, set `$env:PEVAL_WORKBUDDY_RUNTIME_TESTS = '1'` before the `uv run`
command. CI adds the pinned runtime with `--no-deps` to the synced environment
on both Linux and Windows, then checks dependency consistency before integration
tests; the existing dependencies remain at their locked versions.
The Windows gate also exercises actual process-tree ownership and
queries launcher/descendant membership inside an explicitly nested Job;
portable launcher tests use a fake Job handle and do not replace that evidence.

To exercise every present Task in an existing local Office bundle without an
Agent or LLM, set `PEVAL_WORKBUDDY_OFFICE_DATASET` to its root and run
`uv run --no-sync pytest tests/harbor/test_workbuddy_verifier.py -k local_office`.
This opt-in check requires the Office Python packages and verifies native
execution plus source immutability. Scores reflect the initial workspace, not
Agent performance. The normal gate does not require or download that Dataset.

Standalone ATIF tests copy and rename only `atif.py`, then execute it under
`python -I -S` without site packages. They cover valid and invalid evidence,
field-path errors, and non-mutation. Existing conversion tests separately own
normalization and metadata behavior. All source-copy checks isolate user state
and use no real providers, credentials, or WorkBuddy runtime.

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
