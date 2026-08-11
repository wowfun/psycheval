# PBench Scoring

Each Task's `tests/grader.json` defines ordered required calls with explicit
alternative branches, argument constraints, successful observation terms,
exact forbidden tool names, final-answer terms, and optional artifacts.

The required call, its arguments, and its successful observation must use one
complete branch and the same ATIF `tool_call_id`. Evidence from another branch,
another call, or final prose does not satisfy the tool requirement. Later
required rules match later calls.

The verifier writes:

- `verifier/checks.json`: one structured result per observable condition.
- `verifier/reward.json`: binary dimensions for required tool, arguments,
  observation, forbidden tools, final answer, and artifacts, plus total reward
  `1` only when every applicable check passes.

Required artifacts must be relative to the Trial artifact root, non-empty,
regular non-symlink files. Required PNG files must also have a PNG signature.

Live results must distinguish Agent failures from provider, network, browser,
harness, conversion, and upstream-site failures. A correct final statement
without the required structured call evidence receives reward zero.

PBench uses the shared verifier because it reads the Agent trajectory directly.
Harbor 0.21 regrade requires a separate verifier environment and is not part of
this PBench integration.

The normative contracts are
[`specs/015-agent-evaluation`](../../specs/015-agent-evaluation/spec.md) and
[`specs/200-pbench`](../../specs/200-pbench/spec.md).
