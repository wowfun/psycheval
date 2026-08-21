# peval-py Testing

## Scope

This attachment defines deterministic validation for the independently built
Python CLI, Web application bundle, report assets, documentation examples, and
Agent Skill.

## Required Coverage

- Python behavior tests cover input discovery, adapter selection, conversion,
  inspection, reports, serve integration, exports, redaction, and error modes.
- CLI framework tests cover the Typer command tree, trajectory aliases,
  repeatable and optional-value options, plain non-Rich help/errors, stable exit
  codes, and completion script exposure without installing shell configuration.
- The repository Ruff lint and formatting gates include both peval-py's source
  and tests; test helpers use ordinary explicit imports so undefined names
  remain statically detectable. A helper facade declares intentional re-exports
  once in `__all__` rather than using wildcard imports or redundant same-name
  aliases.
- ATIF behavior tests use the public conversion finalizer and validator as the
  primary seam. They cover every adapter's stable identity, UTC timestamps,
  LLM-call classification, portable `extra` facts, tool-result content,
  same-step tool references, token normalization and aggregate invariants.
- Import rejection covers missing required fields, empty or unordered steps,
  wrong types, unknown fields, invalid content parts, dangling tool references,
  and duplicate embedded trajectory identities. Diagnostics identify the exact
  JSON path. Harbor-compatible explicit `null` members in the content union are
  accepted and cross-validated against the public Harbor model.
- Persistence tests establish that validation precedes artifact and catalog
  mutation, invalid existing artifacts remain unchanged, report snapshots use
  the same validation boundary, sidecar mirrors agree with canonical nested
  identities, and inclusive prompt totals drive token rankings without adding
  cached subsets twice.
- Representative exports from every adapter are cross-validated with the
  runtime `harbor==0.21.0` validator. The independent peval-py environment pins
  Python 3.12 and the same Harbor version used by its Dataset workbench.
- Node tests cover browser-state behavior and interaction modules. Type checks
  and the committed bundle check run before the Node test suite.
- Report tests cover exact inference metric projection, weighted aggregate
  parity with serve mode, semantic empty-column hiding, and explicit-zero
  preservation without reading live provider state.
- Behavior tests assert structured results and user-visible invariants rather
  than volatile generated inventories.
- Tests isolate environment, configuration, temporary files, sockets, browser
  state, and timers from the real user profile.
- The Skill passes the standard skill validator and its Python helper scripts
  compile.
- The documented PyInstaller entry builds from
  `src/peval_py/cli/__main__.py`; the binary passes `--help` and a fixture-backed
  report smoke test.
- Repository CI installs peval-py from its own frozen `uv.lock` and runs its
  Python behavior suite independently from the root pytest project. It also uses
  a supported Node version, installs the frozen npm dependency tree, and runs the
  type, committed-bundle, and Node test checks.

Deepagents currently has no committed dedicated fixture or behavior test. Until
the frozen tool source is intentionally reopened, validation includes a
non-committed temporary JSON smoke conversion and reports this coverage gap
honestly.

## Related Topics

- [peval-py](spec.md)
- [310. Evaluation Workspace Testing](../310-eval-workspace/testing.md)
