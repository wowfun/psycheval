# Evaluation Analysis

Analyze the canonical source using the user's evaluation brief and the material
they supplied. Prefer concrete findings over a fixed scorecard. Do not promote
an attached Task, skill, path, report, or live context into an authoritative
criterion unless the brief explicitly establishes that role.

## Method

1. Restate the evaluation questions, target source, supplied basis, expected
   deliverable, constraints, and observable outcome.
2. Read the final response and reward or failure first, then trace backward to
   the events that explain the outcome.
3. Map each evaluation question to observable coverage, partial coverage, a
   supported gap, or unknown. The presence of material in context does not prove
   the Agent used it or that it existed in the same form during the run.
4. Narrow to relevant ATIF step IDs and tool calls instead of loading every
   large event body.
5. Separate retained source evidence, live context observed during analysis,
   user-supplied material, and inference. Record missing, redacted, or
   conversion-limited evidence and never describe live material as Trial-time
   evidence without direct support.
6. Tie every material finding to a phase, retained step, tool call, warning,
   metric, reward, or provenance field.
7. Recommend a concrete change to the skill contract, prompt, orchestration,
   tool interface, argument construction, stopping rule, or evaluation coverage.

## Dimensions

| Dimension | Evidence to inspect |
| --- | --- |
| Evaluation coverage | Questions and expectations stated in the brief, with the supplied basis used only in its stated role. |
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

Hold the Task, evaluation basis, and evaluation bar constant where possible.
Identify the first meaningful divergence before attributing a regression to the
Agent, model, prompt, skill, or tools. Without a controlled comparison, describe
association rather than causation.

Call out changed Tasks, supplied materials, Agents, models, providers, or
regrade provenance when the available evidence supports those differences.
They can invalidate a direct ranking.
