# Trajectory Analysis

Analyze the retained evidence in the context of the task and its evaluation.
Prefer concrete findings over a fixed scorecard.

## Method

1. Establish the task, expected deliverable, constraints, and Harbor evaluation
   outcome.
2. Read the final response and reward or failure first, then trace backward
   through the steps that explain the outcome.
3. Narrow to relevant ATIF step IDs and tool calls instead of loading every
   large event body.
4. Separate observed behavior from inference. Record missing, redacted, or
   conversion-limited evidence.
5. Tie each material finding to a step, tool call, warning, metric, reward, or
   provenance field.
6. Recommend a concrete change to the prompt, orchestration, tool interface,
   argument construction, stopping rule, or evaluation coverage.

## Dimensions

| Dimension | Evidence to inspect |
| --- | --- |
| Task success | Deliverable, final response, verifier outcome, reward dimensions, and failure state. |
| Trajectory quality | Plan coherence, unnecessary detours, repeated work, and use of gathered evidence. |
| Tool use | Tool choice, arguments, ordering, results, missing calls, and redundant calls. |
| Recovery | Errors, retries, fallback behavior, loops, and whether recovery changed the outcome. |
| Grounding | Whether final claims follow from tool results and retained observations. |
| Response quality | Completeness, clarity, instruction following, caveats, and next actions. |
| Performance | Active and wall duration, turns, tool calls, slow steps, and waiting gaps. |
| Cost | Input, output, cache tokens, reported cost, and repeated expensive work. |

Unknown evidence is not zero. Do not assign a latency, cost, error count, or
success state when the retained source does not support it.

## Harbor MultiStep Analysis

Analyze each Harbor step source as its own trajectory. Use its step-level
status, exception, reward, timing, and usage when judging that phase. Use the
parent Trial evaluation only for the overall outcome.

Do not merge event sequences or sum metrics across steps: resumed agents and
adapter-specific exports can preserve overlapping context. Compare source
identity and provenance before treating two steps or Trials as directly
comparable.

If a step lacks a trajectory, report the retained diagnostic and its effect on
the overall Trial. Do not speculate about omitted tool use, reasoning, or final
content.

## Comparisons

Hold the task and evaluation bar constant where possible. Compare outcome,
failure mode, path length, tool behavior, recovery, duration, tokens, cost, and
final response. Identify the first meaningful divergence before attributing a
regression to the model, prompt, or tools.

Call out changed task digests, task versions, agents, models, providers, or
regrade provenance. Those differences can invalidate a direct ranking.

## Written Analysis

When the user requests a report, use Markdown for a narrative review or JSON
for machine-readable findings. Include:

- context and evidence identity;
- executive outcome;
- severity-ranked findings with evidence and impact;
- concrete recommendations;
- relevant metrics;
- limitations and confidence.

Write in the user's language unless requested otherwise. Do not duplicate the
same analysis in multiple formats.
