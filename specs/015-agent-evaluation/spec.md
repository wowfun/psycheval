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

ATIF is the structured record submitted by an Agent or harness. Matching a call
and observation proves internal evidence consistency; Harbor and the verifier do
not independently authenticate that the recorded action occurred. Provenance-
sensitive Agent claims therefore depend on a trusted adapter or independently
retained runtime telemetry. Repository fixtures may synthesize ATIF only for
verifier and integration validation and are not Agent-quality evidence.

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
explicit alternative branches. A branch declares case-sensitive tool-name glob
patterns and may constrain argument values or terms, normalized URL, and
successful observation terms. A pattern without glob metacharacters remains an
exact name. A branch passes only when one call satisfies that branch's tool and
argument constraints and a successful observation with the same `tool_call_id`
satisfies its observation constraints. An observation is unsuccessful when it
is marked as an error, reports a failure status, or reports a non-zero exit
code. Evidence from separate branches or calls may not be combined. Later rules
match calls after the prior fully matched rule. If one rule has several fully
matched calls, its earliest match is the witness for the ordered sequence; a
later duplicate or alternative match does not invalidate a sequence already
established by earlier evidence.

`forbidden_tool_names` uses the same case-sensitive glob semantics. Dataset-owned
configuration enumerates the accepted or forbidden name families explicitly.
Executing a bundled skill is expressed as an ordinary required call: the tool
pattern identifies the execution family, the case-insensitive argument term
identifies the skill name, and the paired observation proves successful
execution. A skill name appearing only in prose or an observation is not call
evidence.

The verifier emits structured checks plus binary `required_tool`,
`required_arguments`, `required_observation`, `forbidden_tools`, `final_answer`,
and `required_artifacts` reward dimensions. A dimension with no applicable
checks scores `1`. The total `reward` is `1` only when every applicable check
passes. Every failed check states the violated observable contract. The final
answer contains every configured static term and the exact root-relative path
of every resolved required artifact. It cannot compensate for a missing
required call, failed observation, wrong parameter, forbidden tool, or missing
artifact.

For a Harbor multi-step Task, each step is scored only from the ATIF trajectory
and artifacts produced by that step's Agent invocation. Evidence from an earlier
step cannot satisfy a later step's required checks or trigger its forbidden-tool
checks. The Agent adapter owns projecting a resumed native session into this
step-local ATIF view; the verifier does not search archived sibling steps or
aggregate their evidence. Harbor owns per-step reward thresholds, early stopping,
and trial-level reward aggregation.

## Artifacts

`required_artifacts` remains a list of strings. Each string is a Trial
artifact-root-relative POSIX glob; a string without glob metacharacters is an
exact path. Absolute paths, backslashes, parent traversal, empty patterns, and
patterns with no matches are rejected. Every match is required and must be a
non-empty regular, non-symlink file; format-invalid required images are also
rejected. The final answer names every matched root-relative POSIX path exactly;
a required path appearing only as a substring of a longer path does not count.

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
