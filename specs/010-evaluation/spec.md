---
name: Evaluation Lifecycle
---

# Evaluation Lifecycle

Evaluation turns a versioned Task and an Agent implementation into inspectable
Trials whose results can be reproduced or explicitly classified as live.

## Scope

This topic owns the Task, Dataset, Trial, and Job lifecycle plus the boundary
between deterministic and live evaluation. Agent evidence semantics belong to
[015. Agent Evaluation](../015-agent-evaluation/spec.md).

## Lifecycle

1. A Task defines one instruction, execution environment, verifier, and task
   metadata.
2. A Dataset selects one or more Tasks without changing their individual
   contracts.
3. A Job resolves an Agent, Dataset, trial count, and execution configuration.
4. Each scheduled attempt creates a Trial with its own paths, trajectory,
   verifier output, reward, exception state, and artifacts.
5. Aggregation computes Job-level outcomes from completed Trial records; it does
   not erase Trial-level failures.

Task definitions and verifier configuration are version-controlled inputs.
Trial artifacts are execution outputs and must never be required to live beside
source code.

## Validation and Live Evaluation

Deterministic validation is split by the interface under test:

- Task verifier validation loads explicit ATIF, source, and artifact fixtures
  directly. It proves Task discovery, authoring contracts, and scoring behavior;
  it does not need to create a Harbor Trial.
- Harbor integration validation uses a small repository-internal synthetic
  harness with representative single-step and multi-step Task fixtures. It
  proves orchestration, paths, resume, artifact transfer, and verifier execution;
  it does not measure Agent quality.

Synthetic evidence is test input rather than an observed Agent execution. It
must be described as such and must not be reported as a real Agent result.

Live evaluation may depend on real Web content, network availability, provider
credentials, model behavior, or browser infrastructure. It is always opt-in and
must report at least these outcomes separately:

- Agent or scoring failure after the evaluation infrastructure operated.
- Harness, provider, network, browser, or upstream-content failure that prevents
  a valid Agent assessment.

A live success is evidence for that run, not a deterministic regression
guarantee.

## Acceptance Criteria

- Every maintained Dataset exposes valid Tasks through Harbor's supported local
  Dataset loading behavior.
- Every maintained Task has deterministic direct verifier coverage using
  explicit fixtures.
- Representative single-step and multi-step integration fixtures produce a
  Harbor Trial, trajectory, verifier checks, reward, and exception status.
- A failed prerequisite does not get reported as an Agent-quality failure.

## Related Topics

- [000. Psycheval Foundation](../000-foundation/spec.md)
- [015. Agent Evaluation](../015-agent-evaluation/spec.md)
- [020. State and Data Model](../020-state-and-data-model/spec.md)
- [200. PBench](../200-pbench/spec.md)
