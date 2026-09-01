# Trajectory Analysis

Analyze retained evidence against the named Task skill and the Task's evaluated
deliverable. Prefer concrete findings over a fixed scorecard.

## Method

1. Establish the Task, skill contract, expected deliverable, constraints, and
   Harbor outcome.
2. Read the final response and reward or failure first, then trace backward to
   the events that explain the outcome.
3. Map the skill's requirements to observable coverage, partial coverage, or a
   supported gap. The mere presence of a skill in context does not prove it was
   used.
4. Narrow to relevant ATIF step IDs and tool calls instead of loading every
   large event body.
5. Separate observed behavior from inference. Record missing, redacted, or
   conversion-limited evidence.
6. Tie every material finding to a phase, retained step, tool call, warning,
   metric, reward, or provenance field.
7. Recommend a concrete change to the skill contract, prompt, orchestration,
   tool interface, argument construction, stopping rule, or evaluation coverage.

## Dimensions

| Dimension | Evidence to inspect |
| --- | --- |
| Skill coverage | Named requirements, triggers, constraints, workflow, outputs, and prohibited actions. |
| Task success | Deliverable, final response, verifier outcome, reward dimensions, and failure state. |
| Trajectory quality | Plan coherence, unnecessary detours, repeated work, and use of gathered evidence. |
| Tool use | Tool choice, arguments, ordering, results, missing calls, and redundant calls. |
| Recovery | Errors, retries, fallback behavior, loops, and whether recovery changed the outcome. |
| Grounding | Whether final claims follow from tool results and retained observations. |
| Performance | Active and wall duration, turns, tool calls, slow steps, and waiting gaps. |
| Cost | Input, output, cache tokens, reported cost, and repeated expensive work. |

Unknown evidence is not zero. Do not assign a latency, cost, error count, skill
violation, or success state when the retained source does not support it.

## MultiStep Trials

Analyze each Harbor phase as its own trajectory. Use phase-level status,
exception, reward, timing, and usage when judging that phase; use the parent
Trial evaluation only for the overall outcome. Do not merge event sequences or
sum metrics across phases because resumed Agents and adapter exports can retain
overlapping context.

If a phase lacks a trajectory, report the retained diagnostic and its effect on
the overall Trial. Do not speculate about omitted tool use, reasoning, or final
content. All phases share one parent Trial report.

## Comparisons

Hold the Task, skill revision, and evaluation bar constant where possible.
Identify the first meaningful divergence before attributing a regression to the
Agent, model, prompt, skill, or tools. Without a controlled comparison, describe
association rather than causation.

Call out changed Task digests, skill revisions, agents, models, providers, or
regrade provenance. These differences can invalidate a direct ranking.
