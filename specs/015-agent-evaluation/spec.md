---
name: Agent Evaluation
---

# Agent Evaluation

Agent evaluation scores observable behavior: ordered calls, their arguments,
their matching observations, required artifacts, and the final answer.

## Scope

This topic defines the shared trajectory evidence and scoring semantics used by
Psycheval evaluations. Dataset-specific facts and required tools belong to the
owning Dataset specification.

## Trajectory Evidence

- Calls and observations remain ordered.
- An observation is evidence for a required call only when it is successful and
  carries the same `tool_call_id`.
- Argument checks are applied to the required call itself, not to final prose or
  a different call.
- Repeated assistant events remain distinct occurrences even if an upstream
  system reuses an item identifier.
- Converters preserve typed tool calls, observations, source blocks, and final
  messages. They do not infer a missing call from citations or prose.

## Scoring

A verifier evaluates ordered `required_calls`. Each rule contains one or more
explicit alternative branches. A branch declares exact accepted tool names and
may constrain argument values or terms, normalized URL, and successful
observation terms. A branch passes only when one call satisfies that branch's
tool and argument constraints and a successful observation with the same
`tool_call_id` satisfies its observation constraints. Evidence from separate
branches or calls may not be combined. Later rules match calls after the prior
fully matched rule. If one rule has several fully matched calls, its earliest
match is the witness for the ordered sequence; a later duplicate or alternative
match does not invalidate a sequence already established by earlier evidence.

Forbidden tools are exact names rather than fuzzy name families. Dataset-owned
configuration enumerates every accepted or forbidden alias.

The verifier emits structured checks plus binary `required_tool`,
`required_arguments`, `required_observation`, `forbidden_tools`, `final_answer`,
and `required_artifacts` reward dimensions. A dimension with no applicable
checks scores `1`. The total `reward` is `1` only when every applicable check
passes. Every failed check states the violated observable contract. A final
answer cannot compensate for a missing required call, failed observation, wrong
parameter, forbidden tool, or missing artifact.

## Artifacts

Required artifact paths are relative to the Trial artifact root. A valid
artifact is a non-empty regular, non-symlink file. Absolute paths, parent
traversal, missing files, and format-invalid required images are rejected.

## Failure Classification

- **Pass:** all required evidence, final terms, and artifacts are valid.
- **Agent failure:** the Trial ran but the Agent violated the Task contract.
- **Harness failure:** the external process or trajectory conversion failed.
- **Infrastructure failure:** the provider, network, browser, environment, or
  upstream site prevented a valid attempt.

## Related Topics

- [010. Evaluation Lifecycle](../010-evaluation/spec.md)
- [020. State and Data Model](../020-state-and-data-model/spec.md)
- [100. Psycheval](../100-psycheval/spec.md)
- [200. PBench](../200-pbench/spec.md)
