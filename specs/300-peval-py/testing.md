# peval-py Testing

## Scope

This attachment defines deterministic validation for the independently built
Python CLI, Web application bundle, report assets, documentation examples, and
Agent Skill.

## Required Coverage

- Python behavior tests cover input discovery, adapter selection, conversion,
  inspection, reports, serve integration, exports, redaction, and error modes.
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
  public `harbor==0.20.0` validator. Harbor remains a development validation
  tool and is not a peval-py runtime dependency.
- Node tests cover browser-state behavior and interaction modules. Type checks
  and the committed bundle check run before the Node test suite.
- Behavior tests assert structured results and user-visible invariants rather
  than volatile generated inventories.
- Tests isolate environment, configuration, temporary files, sockets, browser
  state, and timers from the real user profile.
- The Skill passes the standard skill validator and its Python helper scripts
  compile.
- The documented PyInstaller entry builds from
  `src/peval_py/cli/__main__.py`; the binary passes `--help` and a fixture-backed
  report smoke test.

Deepagents currently has no committed dedicated fixture or behavior test. Until
the frozen tool source is intentionally reopened, validation includes a
non-committed temporary JSON smoke conversion and reports this coverage gap
honestly.

## Related Topics

- [peval-py](spec.md)
- [310. Evaluation Workspace Testing](../310-eval-workspace/testing.md)
