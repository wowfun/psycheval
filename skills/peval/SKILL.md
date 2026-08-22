---
name: peval
description: "Inspect, compare, and analyze retained agent trajectories with peval, especially Harbor Trial directories and their evaluation evidence."
---

# peval

Use this skill to view retained trajectories and produce evidence-backed analysis.
It is read-only: do not modify source databases, trajectory files, Harbor Trial
directories, or workspace annotations.

If `peval` is unavailable, first tell the user to install the checkout once with
`uv tool install -e .`. All subsequent CLI examples and instructions should use
the installed `peval` command.

## Choose Evidence

Prefer a Harbor Trial root when the evaluation produced one:

```console
peval view tr -p <trial-dir>
```

The root preserves the ATIF trajectory together with Harbor task, Job, Trial,
status, reward, timing, failure, and provenance evidence. Passing its
`agent/trajectory.json` directly intentionally reads only that ATIF document.

For a MultiStepTrial, each Harbor step is one source in Harbor result order. A
Harbor step and an ATIF trajectory step are different levels: the former is an
evaluation phase; the latter is an event inside that phase.

Read [view-tr.md](references/view-tr.md) when selecting sources, narrowing steps
or tool calls, comparing sources, or requesting a complete report.

## Analyze

Start with the bounded digest, then request only the steps or tool calls needed
to support a finding. Judge task success from the task and evaluation outcome,
not from the final answer alone. Cite retained step IDs, tool call IDs, rewards,
warnings, timing, usage, or provenance for material claims.

For multiple Harbor steps or Trials, compare each source independently before
using the parent Trial result. Do not concatenate trajectories, sum possibly
overlapping metrics, or replace a step result with the aggregate reward.

If `trajectory_available` is false, analyze only the retained status, exception,
reward, and provenance. Do not infer missing Agent behavior.

Read [analysis-guide.md](references/analysis-guide.md) for analysis dimensions,
comparison method, limitations, and suggested report structure.
