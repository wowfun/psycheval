# PBench Scoring

The Search, Fetch, and Browser Tasks' `tests/grader.json` files define ordered
required calls with explicit alternative branches, argument constraints,
successful observation terms, forbidden tool-name globs, final-answer terms,
and optional artifacts.

The required call, its arguments, and its successful observation must use one
complete branch and the same ATIF `tool_call_id`. Evidence from another branch,
another call, or final prose does not satisfy the tool requirement. Later
required rules match later calls.

ATIF is submitted by the Agent or its harness. Same-call matching establishes
internal consistency in that record; without trusted adapter provenance or
independent runtime telemetry, it does not authenticate that the reported tool
action occurred. Synthetic fixtures validate scoring behavior only.

Required and forbidden tool names are case-sensitive globs. Existing names
without glob metacharacters remain exact. A reported process exit code must be
zero for its observation to count as successful.

The verifier writes:

- `verifier/checks.json`: one structured result per observable condition.
- `verifier/reward.json`: binary dimensions for required tool, arguments,
  observation, forbidden tools, final answer, and artifacts, plus total reward
  `1` only when every applicable check passes.

Each `required_artifacts` entry is a safe root-relative POSIX glob. It must match
at least one non-empty regular non-symlink file, every match is required, and
the final answer must name every matched relative path exactly. Required PNG
files must also have a PNG signature.

Live results must distinguish Agent failures from provider, network, browser,
harness, conversion, and upstream-site failures. A correct final statement
without the required structured call evidence receives reward zero.

PBench uses the shared verifier package because it reads the Agent trajectory
directly and exposes the same `evaluate`/`aggregate` interface to Task-specific
graders.
Harbor 0.21 regrade requires a separate verifier environment and is not part of
this PBench integration.

## Trend Digest

Trend Digest uses a Task-local programmatic verifier for its dynamic source
contracts and reuses the generic verifier's required-call, artifact, and
final-answer checks.
Each step emits `source_evidence`, `freshness`, `coverage`, `format`, binary
`final_answer`, and `reward`. The four quality dimensions retain weights of
30%, 25%, 30%, and 15%; a failed final answer sets the step reward to zero.
Harbor computes the per-key mean across completed steps.

GitHub evidence comes from a successful current-step call for the exact weekly
Trending URL. X and Hacker News express skill execution as `required_calls`
whose Shell-family tool name matches a configured glob, whose arguments contain
the skill name, and whose same-call observation succeeds. That evidence is
combined with the corresponding normalized snapshot. The verifier does not
search archived steps. X fetch failures stay explicit and reduce coverage; a
complete X outage fails the source gate. Live sources are never refetched during
verification.

The normative contracts are
[`specs/015-agent-evaluation`](../../specs/015-agent-evaluation/spec.md) and
[`specs/200-pbench`](../../specs/200-pbench/spec.md).
