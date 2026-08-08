---
name: Psycheval Foundation
---

# Psycheval Foundation

Psycheval is a Harbor-based evaluation system for measuring agent behavior from
observable trajectories and reproducible evidence. Web interaction is the first
evaluation domain, not the product boundary.

## Scope

This topic defines the product purpose, shared vocabulary, engineering
principles, and non-goals used by every other specification.

Psycheval serves evaluation authors, agent implementers, and reviewers who need
to run evaluations, inspect their evidence, and compare results without treating
an agent's final prose as proof of execution.

The system uses these terms consistently:

- A **Task** is one atomic instruction, environment, and verifier contract.
- A **Dataset** is a collection of Tasks.
- A **Trial** is one Agent attempt at one Task.
- A **Job** is an execution that schedules one or more Trials.
- A **trajectory** is the ordered, structured record of the Agent's actions and
  observations.
- A **report** is a derived view over one or more source trajectories or Trials.
- An **evaluation workspace** is local state used to organize sources, reports,
  saved views, and presentation metadata.

## Principles

- Stable behavior has one best-fit specification as its source of truth.
- Interfaces follow real variation seams. Psycheval, PBench, peval-py, and the
  evaluation workspace remain separate modules because they have different
  callers, release surfaces, and dependencies.
- Evidence outranks claims. A successful final answer cannot replace required
  tool calls, observations, artifacts, or verifier checks.
- Default validation is deterministic, local, and isolated. Live providers and
  real Web access are explicit opt-in validation surfaces.
- Derived reports and caches are rebuildable. Original evaluation artifacts and
  user-authored workspace metadata are not silently rewritten.
- Product surfaces minimize cognitive load and omit controls or concepts that do
  not clarify intent, enable action, or protect correctness.
- The repository is pre-release. Clean interfaces take priority over maintaining
  obsolete internal paths or import names.

## Upstream Relationship

Harbor supplies the execution model and public extension interfaces used by
Psycheval. Local specifications reference the exact supported Harbor release and
define only Psycheval-owned behavior or deliberate local restrictions. They do
not reproduce Harbor's complete upstream contract.

ATIF is the interchange format for agent trajectories. Psycheval preserves the
source evidence required to produce a truthful ATIF projection and does not
invent missing calls or observations.

## Non-goals

- Psycheval is not a general workflow orchestrator or an agent runtime.
- PBench is not limited to Psychevo or to Web tasks.
- peval-py is not a runtime dependency of the Psycheval package.
- A taxonomy alone is not justification for a shared code module or adapter.

## Related Topics

- [001. Repository Architecture](../001-architecture/spec.md)
- [010. Evaluation Lifecycle](../010-evaluation/spec.md)
- [015. Agent Evaluation](../015-agent-evaluation/spec.md)
- [020. State and Data Model](../020-state-and-data-model/spec.md)
