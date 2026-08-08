---
name: peval-py
---

# peval-py

peval-py is an independently installable CLI and static-report generator for
normalizing agent session data, inspecting trajectories, and comparing results.

## Scope

This topic owns the CLI product, supported input adapters, normalized reports,
static HTML output, and the companion Agent Skill. Stateful serve behavior
belongs to [310. Evaluation Workspace](../310-eval-workspace/spec.md).

The project remains under `tools/peval-py` with its own Python package, Node
asset build, lockfile, and `peval-py` console command. It is not a dependency of
the root Psycheval distribution.

## Command Interface

The CLI provides conversion, inspection, report generation, and serve workflows
through one command surface. `view tr` defaults to a bounded inspect digest;
callers select `-m raw` when they need a complete JSON or HTML report. The CLI
accepts explicit source paths and input-table
manifests, resolves supported adapters, normalizes sessions, and produces
machine-readable or human-readable output without modifying original sources.

Errors identify the rejected input, adapter, or output condition and exit
non-zero. Optional features such as XLSX manifest reading fail with an actionable
dependency message when their optional runtime dependency is absent.

## Reports

Normalized reports preserve source identity and enough trajectory structure for
inspection, filtering, comparison, export, and workspace import. Static reports
are self-contained artifacts and do not depend on a running local server.

## Acceptance Criteria

- Existing CLI commands, Python import paths, and report behavior remain stable
  during the repository reorganization.
- Every supported adapter can be selected explicitly and participates in the
  documented automatic-selection behavior.
- The Python package and committed Web bundle pass their independent validation
  paths.

## Attachments

- [Inputs and Adapters](inputs.md)
- [Reports](reports.md)
- [Agent Skill](agent-skill.md)
- [Testing](testing.md)

## Related Topics

- [001. Repository Architecture](../001-architecture/spec.md)
- [020. State and Data Model](../020-state-and-data-model/spec.md)
- [310. Evaluation Workspace](../310-eval-workspace/spec.md)
